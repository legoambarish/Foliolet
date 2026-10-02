import json
import re
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from . import wallet_api as api
from . import proof_cache
from .verification import validate_bundle, validate_success
from .decorators import spring_login_required

CATEGORIES = ("Education", "Employment", "Finance", "Identity", "Purchase", "Other")


def page(request, template, **context):
    context.update(product_label=settings.PRODUCT_LABEL, current_username=request.session.get("sb_username"))
    return render(request, "wallet/" + template + ".html", context)


def login(request):
    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        try:
            result = api.call("POST", "/api/auth/login", payload={"username": username, "password": password})
            request.session.cycle_key()
            request.session["sb_auth"] = [username, password]
            request.session["sb_username"] = result["username"]
            request.session["sb_role"] = result["role"]
            return redirect("dashboard:index")
        except api.WalletAPIError as exc:
            error = str(exc)
    return page(request, "login", error=error)


def register(request):
    error = None
    if request.method == "POST":
        password = request.POST.get("password", "")
        if password != request.POST.get("confirm_password"):
            error = "The passwords do not match."
        else:
            try:
                api.call("POST", "/api/auth/register", payload={"username": request.POST.get("username", "").strip(), "password": password, "role": "HOLDER"})
                messages.success(request, "Your account is ready. Sign in to your wallet.")
                return redirect("dashboard:login")
            except api.WalletAPIError as exc:
                error = str(exc)
    return page(request, "register", error=error)


@require_POST
def logout(request):
    request.session.flush()
    return redirect("dashboard:login")


@spring_login_required
def home(request):
    error = None
    docs = []
    try:
        docs = api.call("GET", "/api/wallet/documents", request.session["sb_auth"])
    except api.WalletAPIError as exc:
        error = str(exc)
    category = request.GET.get("category", "")
    query = request.GET.get("q", "").strip()
    filtered = [d for d in docs if (not category or d["category"] == category) and (not query or query.lower() in d["displayName"].lower())]
    return page(request, "home", documents=filtered, categories=CATEGORIES, category=category, query=query, error=error,
                document_count=len(docs), active_count=sum(d["status"] == "ACTIVE" for d in docs), fact_count=sum(d["claimCount"] for d in docs))


@spring_login_required
def enroll(request, previous_id=None):
    error = None
    observations = []
    try:
        observations = api.call("GET", "/api/wallet/integrity/observations", request.session["sb_auth"])
        # First occurrence of each agent/file in received-desc order is the latest report.
        seen = set()
        observations = [o for o in observations if (o["agentId"], o["itemId"]) not in seen and not seen.add((o["agentId"], o["itemId"]))]
        if request.method == "POST":
            file = request.FILES.get("file")
            if not file:
                raise api.WalletAPIError("Choose a document to enroll.", 400)
            endpoint = f"/api/wallet/documents/{previous_id}/versions" if previous_id else "/api/wallet/documents"
            result = api.call("POST", endpoint, request.session["sb_auth"],
                              files={"file": (file.name, file.read(), file.content_type)},
                              data={"displayName": request.POST.get("display_name", ""), "category": request.POST.get("category", "Other"), "observationId": request.POST.get("observation_id", "")})
            return redirect("dashboard:detail", credential_id=result["id"])
    except api.WalletAPIError as exc:
        error = str(exc)
    return page(request, "enroll", categories=CATEGORIES, observations=observations, previous_id=previous_id, error=error)


@spring_login_required
def detail(request, credential_id):
    error = None
    doc = None
    try:
        if request.method == "POST":
            claims = []
            paths = request.POST.getlist("claim_path")
            labels, types, values = (request.POST.getlist(k) for k in ("claim_label", "claim_type", "claim_value"))
            if not (len(paths) == len(labels) == len(types) == len(values)):
                raise api.WalletAPIError("Fact rows were incomplete.", 400)
            for path, label, type_, value in zip(paths, labels, types, values):
                if path.strip() or value.strip():
                    claims.append({"path": path, "label": label, "type": type_, "value": value})
            if request.POST.get("confirm") != "yes":
                raise api.WalletAPIError("Confirm that you have reviewed these facts.", 400)
            api.call("PUT", f"/api/wallet/documents/{credential_id}/claims", request.session["sb_auth"], payload={"claims": claims})
            messages.success(request, "Facts confirmed. Review the commitment, then anchor it.")
            return redirect("dashboard:detail", credential_id=credential_id)
        doc = api.call("GET", f"/api/wallet/documents/{credential_id}", request.session["sb_auth"])
    except api.WalletAPIError as exc:
        if exc.status == 404:
            raise Http404("Document not found") from exc
        error = str(exc)
        try:
            doc = api.call("GET", f"/api/wallet/documents/{credential_id}", request.session["sb_auth"])
        except api.WalletAPIError:
            pass
    rows = doc.get("claims", []) if doc else []
    if request.method == "POST" and error:
        rows = [{"path": p, "label": l, "type": t, "value": v} for p, l, t, v in zip(
            request.POST.getlist("claim_path"), request.POST.getlist("claim_label"), request.POST.getlist("claim_type"), request.POST.getlist("claim_value"))]
    elif not rows and doc and doc.get("status") == "DRAFT":
        rows = doc.get("suggestions", [])
    rows = [r for r in rows if not r.get("derived")]
    if not rows:
        rows = [{"path": "", "label": "", "type": "string", "value": ""}]
    return page(request, "detail", document=doc, claim_rows=rows, error=error)


@spring_login_required
@require_POST
def document_action(request, credential_id, action):
    if action not in ("anchor", "revoke", "integrity"):
        raise Http404
    endpoint = f"/api/wallet/documents/{credential_id}/{action}"
    if action == "integrity" and request.POST.get("restore") == "yes":
        endpoint += "?restore=true"
    try:
        result = api.call("POST", endpoint, request.session["sb_auth"])
        if action == "integrity":
            getattr(messages, "success" if result["intact"] else "warning")(request, result["message"])
        else:
            messages.success(request, "Commitment anchored." if action == "anchor" else "Credential revoked on-chain.")
    except api.WalletAPIError as exc:
        messages.error(request, str(exc))
    return redirect("dashboard:detail", credential_id=credential_id)


@spring_login_required
def original(request, credential_id):
    try:
        content, disposition = api.call("GET", f"/api/wallet/documents/{credential_id}/file", request.session["sb_auth"], binary=True)
    except api.WalletAPIError as exc:
        messages.error(request, str(exc))
        return redirect("dashboard:detail", credential_id=credential_id)
    response = HttpResponse(content, content_type="application/octet-stream")
    response["Content-Disposition"] = disposition
    return response


@spring_login_required
def compose(request, credential_id):
    error = None
    doc = None
    try:
        doc = api.call("GET", f"/api/wallet/documents/{credential_id}", request.session["sb_auth"])
        if request.method == "POST":
            minutes = int(request.POST.get("expires_minutes", "30"))
            result = api.call("POST", "/api/wallet/disclosures", request.session["sb_auth"], payload={
                "credentialId": credential_id, "claimIds": request.POST.getlist("claims"),
                "verifierLabel": request.POST.get("verifier_label", ""), "purpose": request.POST.get("purpose", ""),
                "expiresInMinutes": minutes, "oneTime": request.POST.get("one_time") == "yes"})
            return page(request, "share_ready", share=result)
    except (api.WalletAPIError, ValueError) as exc:
        error = str(exc) if isinstance(exc, api.WalletAPIError) else "Choose a valid expiry."
    return page(request, "compose", document=doc, error=error)


@spring_login_required
def sharing(request):
    grants, events, error = [], [], None
    try:
        grants = api.call("GET", "/api/wallet/disclosures", request.session["sb_auth"])
        events = api.call("GET", "/api/wallet/activity", request.session["sb_auth"])
    except api.WalletAPIError as exc:
        error = str(exc)
    return page(request, "sharing", grants=grants, events=events, error=error)


@spring_login_required
@require_POST
def revoke_share(request, grant_id):
    try:
        api.call("POST", f"/api/wallet/disclosures/{grant_id}/revoke", request.session["sb_auth"])
        messages.success(request, "Proof link revoked. Previously downloaded facts cannot be recalled.")
    except api.WalletAPIError as exc:
        messages.error(request, str(exc))
    return redirect("dashboard:sharing")


@spring_login_required
def integrity(request):
    agents, observations, paired, error = [], [], None, None
    try:
        if request.method == "POST":
            paired = api.call("POST", "/api/wallet/integrity/agents", request.session["sb_auth"], payload={"label": request.POST.get("label", "")})
        agents = api.call("GET", "/api/wallet/integrity/agents", request.session["sb_auth"])
        observations = api.call("GET", "/api/wallet/integrity/observations", request.session["sb_auth"])
    except api.WalletAPIError as exc:
        error = str(exc)
    return page(request, "integrity", agents=agents, observations=observations, paired=paired, error=error)


@spring_login_required
@require_POST
def revoke_agent(request, agent_id):
    try:
        api.call("POST", f"/api/wallet/integrity/agents/{agent_id}/revoke", request.session["sb_auth"])
        messages.success(request, "Integrity agent revoked. Historical observations are retained.")
    except api.WalletAPIError as exc:
        messages.error(request, str(exc))
    return redirect("dashboard:integrity")


def verify(request, token):
    if not re.fullmatch(r"[0-9a-f]{64}", token):
        raise Http404
    result, error = None, None
    if request.method == "POST":
        try:
            candidate = api.call("POST", f"/api/public/disclosures/{token}/open")
            if not isinstance(candidate, dict):
                raise ValueError("Invalid verification response")
            validate_success(candidate.get("verification"))
            validate_bundle(candidate.get("bundle"))
            # Cache only already released facts for session-bound export. Never re-open a one-time grant.
            released = request.session.get("released_proofs", {})
            released[candidate["bundle"]["presentation"]["grantId"]] = proof_cache.seal(candidate["bundle"])
            request.session["released_proofs"] = dict(list(released.items())[-5:])
            result = candidate
        except api.WalletAPIError as exc:
            error = str(exc)
        except (ValueError, TypeError, KeyError):
            error = "The service did not return a valid successful verification. No facts were accepted."
    return page(request, "verify", result=result, error=error, network=settings.TRUSTED_DEPLOYMENT,
                public=True, rpc_url=settings.PUBLIC_EVM_RPC_URL)


def proof_status(request, grant_id):
    try:
        return JsonResponse(api.call("GET", f"/api/public/grants/{grant_id}/status"))
    except api.WalletAPIError as exc:
        return JsonResponse({"status": "UNAVAILABLE", "message": str(exc)}, status=exc.status)


def proof_download(request, grant_id):
    sealed = request.session.get("released_proofs", {}).get(grant_id)
    if not sealed:
        raise Http404("Open this proof in this browser before downloading it")
    try:
        bundle = proof_cache.open_proof(grant_id, sealed)
        validate_bundle(bundle)
        if bundle["presentation"]["grantId"] != grant_id:
            raise ValueError("Wrong presentation")
    except (ValueError, TypeError, KeyError):
        released = request.session.get("released_proofs", {})
        released.pop(grant_id, None)
        request.session["released_proofs"] = released
        raise Http404("Open a fresh presentation before downloading it")
    try:
        verified = api.call("POST", "/api/public/verify-bundle", payload=bundle)
        validate_success(verified)
    except (ValueError, TypeError, KeyError):
        released = request.session.get("released_proofs", {})
        released.pop(grant_id, None)
        request.session["released_proofs"] = released
        return HttpResponse("This presentation is no longer current; ask for a fresh proof.", status=410)
    except api.WalletAPIError:
        return HttpResponse("Current proof verification is unavailable.", status=503)
    response = JsonResponse(bundle, json_dumps_params={"indent": 2})
    response["Content-Disposition"] = 'attachment; filename="disclosure-proof.json"'
    return response
