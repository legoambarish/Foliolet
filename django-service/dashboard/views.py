from django.shortcuts import render, redirect
from django.http import Http404
from django.contrib import messages

from . import api_client
from .decorators import spring_login_required


def login_view(request):
    """
    Logs the dashboard user in by verifying their credentials against
    Spring Boot's /api/auth/login, then stores the (username, password)
    tuple in the session for use as Basic Auth on every later API call,
    and the returned role/username for display and access decisions.
    """
    error = None

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        try:
            result = api_client.login(username, password)
            request.session["sb_auth"] = (username, password)
            request.session["sb_role"] = result.get("role")
            request.session["sb_username"] = result.get("username", username)
            return redirect("dashboard:index")
        except api_client.SpringBootAuthError:
            error = "Invalid username or password."
        except api_client.SpringBootAPIError:
            error = "Could not reach the document service. Is Spring Boot running?"

    return render(request, "dashboard/login.html", {"error": error})


def logout_view(request):
    request.session.flush()
    return redirect("dashboard:login")


@spring_login_required
def hub(request):
    """
    Home/landing hub: a quiet entry point with tiles into Case Registry,
    Documents, and Audit Log, plus a small recent-activity glance. The
    full case table used to live here — it now has its own page at
    /cases/ so the root URL isn't doing double duty as a data table.
    """
    auth = request.session.get("sb_auth")
    restricted = False
    case_count = 0
    recent_activity = []

    try:
        cases = api_client.get_cases(auth=auth)
        case_count = len(cases)
        recent_activity = api_client.get_audit_log(auth=auth)[:3]
    except api_client.SpringBootAPIError:
        restricted = True

    context = {
        "case_count": case_count,
        "recent_activity": recent_activity,
        "restricted": restricted,
        "using_stub": api_client.USE_STUB,
        "current_username": request.session.get("sb_username"),
        "current_role": request.session.get("sb_role"),
    }
    return render(request, "dashboard/hub.html", context)


@spring_login_required
def case_registry(request):
    """
    Case Registry: list of cases with document counts, plus recent
    activity across all cases. This is what used to render at the root
    URL — same logic, new home at /cases/.
    """
    auth = request.session.get("sb_auth")
    restricted = False

    try:
        cases = api_client.get_cases(auth=auth)
        recent_activity = api_client.get_audit_log(auth=auth)[:5]
    except api_client.SpringBootAPIError:
        cases = []
        recent_activity = []
        restricted = True

    context = {
        "cases": cases,
        "recent_activity": recent_activity,
        "restricted": restricted,
        "using_stub": api_client.USE_STUB,
        "current_username": request.session.get("sb_username"),
        "current_role": request.session.get("sb_role"),
    }
    return render(request, "dashboard/case_registry.html", context)

@spring_login_required
def case_detail(request, case_id):
    """
    Single case view: case metadata, its documents, and its audit trail.

    get_case_detail and the audit log call are ADMIN-only on the Spring
    Boot side, an OFFICER can still see the case's documents (that
    endpoint is authenticated-only) but not its case summary or audit
    trail, handled below rather than crashing.
    """
    auth = request.session.get("sb_auth")
    restricted = False

    try:
        case = api_client.get_case_detail(case_id, auth=auth)
    except api_client.SpringBootAPIError:
        case = None
        restricted = True

    if case is None and not restricted:
        raise Http404(f"No case found with ID {case_id}")

    documents = api_client.get_documents(case_id=case_id, auth=auth)

    try:
        audit_log = api_client.get_audit_log(case_id=case_id, auth=auth)
    except api_client.SpringBootAPIError:
        audit_log = []
        restricted = True

    context = {
        "case": case or {"caseId": case_id, "title": case_id, "status": ""},
        "documents": documents,
        "audit_log": audit_log,
        "restricted": restricted,
        "using_stub": api_client.USE_STUB,
        "current_username": request.session.get("sb_username"),
        "current_role": request.session.get("sb_role"),
    }
    return render(request, "dashboard/case_detail.html", context)


@spring_login_required
def document_list(request):
    """
    Filterable document listing. Reads optional query params:
    ?case_id=&type=&from=&to=
    """
    auth = request.session.get("sb_auth")
    case_id = request.GET.get("case_id") or None
    document_type = request.GET.get("type") or None
    date_from = request.GET.get("from") or None
    date_to = request.GET.get("to") or None

    documents = api_client.get_documents(
        case_id=case_id,
        document_type=document_type,
        date_from=date_from,
        date_to=date_to,
        auth=auth,
    )

    context = {
        "documents": documents,
        "filters": {
            "case_id": case_id or "",
            "type": document_type or "",
            "from": date_from or "",
            "to": date_to or "",
        },
        "using_stub": api_client.USE_STUB,
        "current_username": request.session.get("sb_username"),
        "current_role": request.session.get("sb_role"),
    }
    return render(request, "dashboard/document_list.html", context)


@spring_login_required
def audit_log(request):
    """
    Full activity/audit trail view, optionally scoped by ?case_id=.
    ADMIN-only on the Spring Boot side, handled gracefully for an
    OFFICER session rather than crashing.
    """
    auth = request.session.get("sb_auth")
    case_id = request.GET.get("case_id") or None
    restricted = False

    try:
        entries = api_client.get_audit_log(case_id=case_id, auth=auth)
    except api_client.SpringBootAPIError:
        entries = []
        restricted = True

    context = {
        "entries": entries,
        "case_id": case_id or "",
        "restricted": restricted,
        "using_stub": api_client.USE_STUB,
        "current_username": request.session.get("sb_username"),
        "current_role": request.session.get("sb_role"),
    }
    return render(request, "dashboard/audit_log.html", context)


@spring_login_required
def upload_document(request):
    """
    Upload a new document. GET shows the form, POST submits it.
    Any authenticated user (OFFICER or ADMIN) can upload, matching the
    Spring Boot side (POST /api/documents just requires authentication,
    not a specific role).
    """
    auth = request.session.get("sb_auth")
    error = None

    if request.method == "POST":
        uploaded_file = request.FILES.get("file")
        case_id = request.POST.get("case_id", "").strip()
        document_type = request.POST.get("document_type", "").strip()

        if not uploaded_file or not case_id or not document_type:
            error = "File, case ID, and document type are all required."
        else:
            try:
                result = api_client.upload_document(uploaded_file, case_id, document_type, auth=auth)
                warning = result.get("preUploadWarning") if isinstance(result, dict) else None
                if warning:
                    messages.warning(request, f"Uploaded, but with a concern: {warning}")
                else:
                    messages.success(request, f"Uploaded '{uploaded_file.name}' to case {case_id}.")
                return redirect("dashboard:document_list")
            except api_client.SpringBootAPIError:
                error = "Could not reach the document service. Is Spring Boot running?"

    context = {
        "error": error,
        "using_stub": api_client.USE_STUB,
        "current_username": request.session.get("sb_username"),
        "current_role": request.session.get("sb_role"),
    }
    return render(request, "dashboard/upload_document.html", context)


@spring_login_required
def edit_document(request, document_id):
    """
    Edit a document's metadata (case ID, document type). Spring Boot
    enforces owner-or-ADMIN, a 403 from there is surfaced as a plain
    error message here rather than a stack trace.
    """
    auth = request.session.get("sb_auth")
    error = None

    if request.method == "POST":
        case_id = request.POST.get("case_id", "").strip()
        document_type = request.POST.get("document_type", "").strip()
        try:
            api_client.update_document(document_id, case_id=case_id, document_type=document_type, auth=auth)
            messages.success(request, f"Updated document {document_id}.")
            return redirect("dashboard:document_list")
        except api_client.SpringBootPermissionError:
            error = "You do not have permission to edit this document."
        except api_client.SpringBootAPIError:
            error = "Could not reach the document service. Is Spring Boot running?"

    context = {
        "document_id": document_id,
        "error": error,
        "using_stub": api_client.USE_STUB,
        "current_username": request.session.get("sb_username"),
        "current_role": request.session.get("sb_role"),
    }
    return render(request, "dashboard/edit_document.html", context)


@spring_login_required
def delete_document(request, document_id):
    """
    Delete a document. Requires a POST (a GET must never delete
    anything), a confirmation page is shown first on GET.
    """
    auth = request.session.get("sb_auth")

    if request.method == "POST":
        try:
            api_client.delete_document(document_id, auth=auth)
            messages.success(request, f"Deleted document {document_id}.")
        except api_client.SpringBootPermissionError:
            messages.error(request, "You do not have permission to delete this document.")
        except api_client.SpringBootAPIError:
            messages.error(request, "Could not reach the document service. Is Spring Boot running?")
        return redirect("dashboard:document_list")

    context = {
        "document_id": document_id,
        "using_stub": api_client.USE_STUB,
        "current_username": request.session.get("sb_username"),
        "current_role": request.session.get("sb_role"),
    }
    return render(request, "dashboard/delete_document_confirm.html", context)

@spring_login_required
def verify_document(request, document_id):
    """
    Triggers Spring Boot's tamper check for a document and shows the
    result as a message. This is a read-only check (GET, not a mutation),
    unlike delete it doesn't need a confirm-first page.
    """
    auth = request.session.get("sb_auth")

    try:
        result = api_client.verify_document(document_id, auth=auth)
        if result.get("restored"):
            messages.warning(request, f"Document {document_id}: {result.get('message')}")
        elif result.get("tampered"):
            messages.error(request, f"Document {document_id}: {result.get('message')}")
        else:
            messages.success(request, f"Document {document_id}: {result.get('message')}")
    except api_client.SpringBootPermissionError:
        messages.error(request, "You do not have permission to verify this document.")
    except api_client.SpringBootAPIError:
        messages.error(request, "Could not reach the document service. Is Spring Boot running?")

    return redirect("dashboard:document_list")

@spring_login_required
def ai_document_analysis(request, document_id):
    """
    AI Document Analysis page for a single document. GET shows the most
    recent stored analysis if one exists. POST (the "Run Analysis" button)
    triggers a fresh run and blocks until the LLM call completes.
    """
    auth = request.session.get("sb_auth")
    error = None
    analysis = None

    if request.method == "POST":
        try:
            analysis = api_client.analyze_document(document_id, auth=auth)
            messages.success(request, "Analysis complete.")
        except api_client.SpringBootPermissionError:
            error = "You do not have permission to analyze this document."
        except api_client.SpringBootAPIError:
            error = "Could not reach the document service, or the AI call failed. Is Spring Boot running, and is the OpenRouter key configured?"
    else:
        try:
            analysis = api_client.get_document_analysis(document_id, auth=auth)
        except api_client.SpringBootAPIError:
            error = "Could not reach the document service. Is Spring Boot running?"

    context = {
        "document_id": document_id,
        "analysis": analysis,
        "error": error,
        "using_stub": api_client.USE_STUB,
        "current_username": request.session.get("sb_username"),
        "current_role": request.session.get("sb_role"),
    }
    return render(request, "dashboard/document_analysis.html", context)
