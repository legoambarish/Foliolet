"""
api_client.py

Single point of contact between the Django reporting/oversight service and the
Spring Boot system-of-record service.

Phase 2 goal: let the dashboard views be built and demoed *before* the real
Spring Boot endpoints exist, by returning data shaped exactly like the real
API contract will be. When Spring Boot is ready, flip USE_STUB to False (or
set DJANGO_USE_STUB_API=false in the environment) and nothing in views.py
has to change, because the return shapes are identical either way.

Expected real endpoints (Spring Boot side, for reference):
    GET  /api/cases                      -> list of case summaries
    GET  /api/cases/{caseId}              -> single case detail
    GET  /api/documents?caseId=&type=&from=&to=  -> filtered document list
    GET  /api/audit-log?caseId=&documentId=      -> audit trail entries
    POST /api/auth/login                  -> {token, role, username}
"""

import os
from datetime import datetime, timedelta

import requests
from django.conf import settings

# Toggle: True while Spring Boot isn't ready / isn't reachable from here.
# Read from settings.py first, fall back to an env var, default to stub mode.
USE_STUB = getattr(
    settings,
    "USE_STUB_API",
    os.environ.get("DJANGO_USE_STUB_API", "true").lower() == "true",
)

BASE_URL = getattr(settings, "SPRING_BOOT_API_BASE_URL", "http://localhost:8080")
REQUEST_TIMEOUT_SECONDS = 5

# Fallback only, used if a view somehow calls this without a logged-in
# session's credentials (e.g. stub mode, or a bug). Real requests should
# always pass the auth tuple stored in the user's Django session by
# login_view, not rely on this.
DASHBOARD_ADMIN_USERNAME = os.environ.get("DASHBOARD_ADMIN_USERNAME", "admin")
DASHBOARD_ADMIN_PASSWORD = os.environ.get("DASHBOARD_ADMIN_PASSWORD", "changeme")
_FALLBACK_AUTH = (DASHBOARD_ADMIN_USERNAME, DASHBOARD_ADMIN_PASSWORD)


class SpringBootAPIError(Exception):
    """Raised when the real Spring Boot API call fails or returns a non-2xx status."""
    pass


class SpringBootAuthError(Exception):
    """Raised specifically when Spring Boot's /api/auth/login rejects credentials."""
    pass


class SpringBootPermissionError(Exception):
    """Raised when Spring Boot returns 403, the logged-in user isn't the
    document's owner and isn't an ADMIN."""
    pass


# ---------------------------------------------------------------------------
# Stub data
# ---------------------------------------------------------------------------
# Shaped to mirror the real DocumentRecord / AuditLog / User entities so that
# swapping stub -> real is a data-source change only, not a shape change.

_NOW = datetime(2026, 8, 27, 10, 0, 0)

_STUB_CASES = [
    {"caseId": "CASE-2026-0142", "title": "Missing Persons - Sector 12", "status": "OPEN", "documentCount": 7},
    {"caseId": "CASE-2026-0157", "title": "Assault Investigation - MG Road", "status": "OPEN", "documentCount": 4},
    {"caseId": "CASE-2026-0099", "title": "Cyber Harassment Complaint", "status": "CLOSED", "documentCount": 11},
]

_STUB_DOCUMENTS = [
    {
        "documentId": "DOC-1001", "caseId": "CASE-2026-0142", "documentType": "FIR",
        "title": "FIR Copy - Sector 12", "uploadedBy": "officer.rao",
        "uploadedAt": (_NOW - timedelta(days=5)).isoformat(),
    },
    {
        "documentId": "DOC-1002", "caseId": "CASE-2026-0142", "documentType": "WITNESS_STATEMENT",
        "title": "Witness Statement - S. Iyer", "uploadedBy": "officer.rao",
        "uploadedAt": (_NOW - timedelta(days=4)).isoformat(),
    },
    {
        "documentId": "DOC-1003", "caseId": "CASE-2026-0157", "documentType": "FORENSIC_REPORT",
        "title": "Forensic Report - MG Road Incident", "uploadedBy": "officer.singh",
        "uploadedAt": (_NOW - timedelta(days=2)).isoformat(),
    },
    {
        "documentId": "DOC-1004", "caseId": "CASE-2026-0099", "documentType": "CHARGE_SHEET",
        "title": "Charge Sheet - Cyber Harassment", "uploadedBy": "officer.menon",
        "uploadedAt": (_NOW - timedelta(days=30)).isoformat(),
    },
]

_STUB_AUDIT_LOG = [
    {
        "auditId": "AUD-9001", "documentId": "DOC-1001", "caseId": "CASE-2026-0142",
        "action": "UPLOAD", "performedBy": "officer.rao",
        "performedAt": (_NOW - timedelta(days=5)).isoformat(),
    },
    {
        "auditId": "AUD-9002", "documentId": "DOC-1001", "caseId": "CASE-2026-0142",
        "action": "VIEW", "performedBy": "admin.kapoor",
        "performedAt": (_NOW - timedelta(days=3)).isoformat(),
    },
    {
        "auditId": "AUD-9003", "documentId": "DOC-1003", "caseId": "CASE-2026-0157",
        "action": "VIEW", "performedBy": "officer.singh",
        "performedAt": (_NOW - timedelta(hours=6)).isoformat(),
    },
    {
        "auditId": "AUD-9004", "documentId": "DOC-1004", "caseId": "CASE-2026-0099",
        "action": "EDIT", "performedBy": "officer.menon",
        "performedAt": (_NOW - timedelta(days=1)).isoformat(),
    },
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get(path, params=None, auth=None):
    """Perform a real GET call against the Spring Boot service.

    auth is the (username, password) tuple for the logged-in dashboard
    user, stored in their Django session by login_view. Django's session
    backend serializes to JSON, so a tuple comes back out as a list,
    which the requests library will not accept as Basic Auth (it checks
    specifically for a tuple), hence the explicit tuple() conversion
    below.
    """
    url = f"{BASE_URL}{path}"
    resolved_auth = tuple(auth) if auth else _FALLBACK_AUTH
    try:
        response = requests.get(
            url,
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
            auth=resolved_auth,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise SpringBootAPIError(f"Failed calling {url}: {exc}") from exc


def _post_multipart(path, files, data, auth=None):
    """POST a multipart/form-data request (file upload)."""
    url = f"{BASE_URL}{path}"
    resolved_auth = tuple(auth) if auth else _FALLBACK_AUTH
    try:
        response = requests.post(
            url,
            files=files,
            data=data,
            timeout=REQUEST_TIMEOUT_SECONDS,
            auth=resolved_auth,
        )
        if response.status_code == 403:
            raise SpringBootPermissionError("Not authorized to perform this action")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise SpringBootAPIError(f"Failed calling {url}: {exc}") from exc


def _put_json(path, json_body, auth=None):
    """PUT a JSON body against the Spring Boot service."""
    url = f"{BASE_URL}{path}"
    resolved_auth = tuple(auth) if auth else _FALLBACK_AUTH
    try:
        response = requests.put(
            url,
            json=json_body,
            timeout=REQUEST_TIMEOUT_SECONDS,
            auth=resolved_auth,
        )
        if response.status_code == 403:
            raise SpringBootPermissionError("Not authorized to perform this action")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise SpringBootAPIError(f"Failed calling {url}: {exc}") from exc


def _delete(path, auth=None):
    """DELETE against the Spring Boot service. No response body expected."""
    url = f"{BASE_URL}{path}"
    resolved_auth = tuple(auth) if auth else _FALLBACK_AUTH
    try:
        response = requests.delete(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            auth=resolved_auth,
        )
        if response.status_code == 403:
            raise SpringBootPermissionError("Not authorized to perform this action")
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SpringBootAPIError(f"Failed calling {url}: {exc}") from exc


def _filter_documents(case_id=None, document_type=None, date_from=None, date_to=None):
    results = _STUB_DOCUMENTS
    if case_id:
        results = [d for d in results if d["caseId"] == case_id]
    if document_type:
        results = [d for d in results if d["documentType"] == document_type]
    if date_from:
        results = [d for d in results if d["uploadedAt"] >= date_from]
    if date_to:
        results = [d for d in results if d["uploadedAt"] <= date_to]
    return results


def _filter_audit_log(case_id=None, document_id=None):
    results = _STUB_AUDIT_LOG
    if case_id:
        results = [a for a in results if a["caseId"] == case_id]
    if document_id:
        results = [a for a in results if a["documentId"] == document_id]
    return sorted(results, key=lambda a: a["performedAt"], reverse=True)


# ---------------------------------------------------------------------------
# Public API - this is what views.py calls. Shape is identical stub or real.
# ---------------------------------------------------------------------------

def login(username, password):
    """
    Verify credentials against Spring Boot's /api/auth/login.
    Returns the parsed {token, role, username} dict on success.
    Raises SpringBootAuthError on bad credentials, SpringBootAPIError
    on any other failure (Spring Boot unreachable, etc).
    In stub mode, any non-empty username/password is accepted as ADMIN,
    since there is no real Spring Boot to check against.
    """
    if USE_STUB:
        if not username or not password:
            raise SpringBootAuthError("Username and password are required")
        return {"token": "stub-token", "role": "ADMIN", "username": username}

    url = f"{BASE_URL}/api/auth/login"
    try:
        response = requests.post(
            url,
            json={"username": username, "password": password},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise SpringBootAPIError(f"Failed calling {url}: {exc}") from exc

    if response.status_code == 401:
        raise SpringBootAuthError("Invalid username or password")
    response.raise_for_status()
    return response.json()


def get_cases(auth=None):
    """Return a list of case summaries for the overview page."""
    if USE_STUB:
        return _STUB_CASES
    return _get("/api/cases", auth=auth)


def get_case_detail(case_id, auth=None):
    """Return a single case's detail, or None if not found."""
    if USE_STUB:
        return next((c for c in _STUB_CASES if c["caseId"] == case_id), None)
    return _get(f"/api/cases/{case_id}", auth=auth)


def get_documents(case_id=None, document_type=None, date_from=None, date_to=None, auth=None):
    """Return documents, optionally filtered by case, type, and date range."""
    if USE_STUB:
        return _filter_documents(case_id, document_type, date_from, date_to)
    params = {
        "caseId": case_id,
        "type": document_type,
        "from": date_from,
        "to": date_to,
    }
    params = {k: v for k, v in params.items() if v}
    return _get("/api/documents", params=params, auth=auth)


def get_audit_log(case_id=None, document_id=None, auth=None):
    """Return audit trail entries, most recent first, optionally scoped to a case or document."""
    if USE_STUB:
        return _filter_audit_log(case_id, document_id)
    params = {k: v for k, v in {"caseId": case_id, "documentId": document_id}.items() if v}
    return _get("/api/audit-log", params=params, auth=auth)


def upload_document(file, case_id, document_type, auth=None):
    """
    Upload a new document. In stub mode, appends an in-memory fake
    record so the flow is demoable without Spring Boot, this is not
    persisted anywhere and resets on server restart.
    """
    if USE_STUB:
        new_id = f"DOC-{1000 + len(_STUB_DOCUMENTS) + 1}"
        record = {
            "documentId": new_id,
            "caseId": case_id,
            "documentType": document_type,
            "title": getattr(file, "name", "uploaded-file"),
            "uploadedBy": "stub-user",
            "uploadedAt": datetime.now().isoformat(),
        }
        _STUB_DOCUMENTS.append(record)
        return record

    return _post_multipart(
        "/api/documents",
        files={"file": (file.name, file.read(), file.content_type)},
        data={"caseId": case_id, "documentType": document_type},
        auth=auth,
    )
AI_ANALYSIS_TIMEOUT_SECONDS = 60  # LLM calls take longer than ordinary CRUD calls


def analyze_document(document_id, auth=None):
    """
    Triggers a fresh AI analysis run against Spring Boot for this document.
    Synchronous, the request blocks until the LLM call completes.
    """
    if USE_STUB:
        return {
            "documentId": document_id,
            "summary": "Stub mode: this is a placeholder summary, no real analysis was run.",
            "keyDates": [],
            "keyParties": [],
            "flaggedClauses": [],
            "analyzedAt": None,
        }

    url = f"{BASE_URL}/api/documents/{document_id}/analyze"
    resolved_auth = tuple(auth) if auth else _FALLBACK_AUTH
    try:
        response = requests.post(url, timeout=AI_ANALYSIS_TIMEOUT_SECONDS, auth=resolved_auth)
        if response.status_code == 403:
            raise SpringBootPermissionError("Not authorized to perform this action")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise SpringBootAPIError(f"Failed calling {url}: {exc}") from exc


def get_document_analysis(document_id, auth=None):
    """Returns the most recent stored analysis, or None if never analyzed."""
    if USE_STUB:
        return None

    url = f"{BASE_URL}/api/documents/{document_id}/analysis"
    resolved_auth = tuple(auth) if auth else _FALLBACK_AUTH
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS, auth=resolved_auth)
        if response.status_code == 204:
            return None
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise SpringBootAPIError(f"Failed calling {url}: {exc}") from exc


def update_document(document_id, case_id=None, document_type=None, auth=None):
    """
    Update a document's metadata (caseId and/or documentType). In stub
    mode, mutates the in-memory record.
    """
    if USE_STUB:
        for d in _STUB_DOCUMENTS:
            if d["documentId"] == document_id:
                if case_id:
                    d["caseId"] = case_id
                if document_type:
                    d["documentType"] = document_type
                return d
        raise SpringBootAPIError(f"No stub document with id {document_id}")

    body = {k: v for k, v in {"caseId": case_id, "documentType": document_type}.items() if v}
    return _put_json(f"/api/documents/{document_id}", body, auth=auth)

def verify_document(document_id, auth=None):
    """
    Ask Spring Boot to recompute the file's hash and compare it against
    the on-chain record. In stub mode, always reports a match, there is
    no real blockchain behind stub data.
    """
    if USE_STUB:
        return {"documentId": document_id, "tampered": False, "restored": False, "message": "Stub mode: no real verification performed."}

    return _get(f"/api/documents/{document_id}/verify", auth=auth)

def delete_document(document_id, auth=None):
    """Delete a document. In stub mode, removes it from the in-memory list."""
    if USE_STUB:
        global _STUB_DOCUMENTS
        _STUB_DOCUMENTS = [d for d in _STUB_DOCUMENTS if d["documentId"] != document_id]
        return

    _delete(f"/api/documents/{document_id}", auth=auth)
