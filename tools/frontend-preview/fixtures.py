"""Fictional, obviously synthetic data for the offline design preview. No real people or documents."""

ROOT = "0x7d1c4e9a0b2f63d58e1a47c0d9b3f2a6e8c51b7d40a9f3e2c6b8d1a5f0e4c3b2"
CONTRACT = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
TX = "0x9a3f6c1e8b2d4f70a5c39e1d6b8f2a4c7e0d3b5a9f1c6e8d2b4a7c0f3e5d9b1a"

INTAKE_DIGI = {"indicator": "POSSIBLE_DIGILOCKER_FORMAT", "method": "WATCHER_ASSISTED", "lineage": "SUGGESTIONS_MODIFIED", "format": "pdf"}
INTAKE_PLAIN = {"indicator": "NO_DIGILOCKER_INDICATOR", "method": "MANUAL", "lineage": "SUGGESTIONS_UNMODIFIED", "format": "pdf"}
INTAKE_MANUAL = {"indicator": "INCONCLUSIVE", "method": "MANUAL", "lineage": "MANUAL", "format": "png"}
INTAKE_STALE = {"indicator": "POSSIBLE_DIGILOCKER_FORMAT", "method": "MANUAL", "lineage": "STALE_SOURCE", "format": "pdf"}

DOCUMENTS = [
    {"id": "doc-active-31c9", "displayName": "Semester 6 marksheet", "category": "Education", "version": 2, "claimCount": 6,
     "status": "ACTIVE", "provenanceLevel": "FIRST_SEEN_TRACKED", "intake": INTAKE_DIGI},
    {"id": "doc-draft-7f2a", "displayName": "Salary slip — September 2026 (Northwind Analytics Pvt. Ltd., Bengaluru office)",
     "category": "Employment", "version": 1, "claimCount": 0, "status": "DRAFT", "provenanceLevel": "SELF_ENROLLED", "intake": INTAKE_PLAIN},
    {"id": "doc-ready-55e0", "displayName": "Rental agreement, Koramangala flat", "category": "Other", "version": 1, "claimCount": 4,
     "status": "DRAFT", "merkleRoot": ROOT, "provenanceLevel": "SELF_ENROLLED", "intake": INTAKE_MANUAL},
    {"id": "doc-pending-9d10", "displayName": "Bank statement Q3", "category": "Finance", "version": 1, "claimCount": 5,
     "status": "ANCHOR_PENDING", "provenanceLevel": "SELF_ENROLLED", "intake": INTAKE_STALE},
    {"id": "doc-id-2c77", "displayName": "PAN card", "category": "Identity", "version": 1, "claimCount": 3,
     "status": "ACTIVE", "provenanceLevel": "SELF_ENROLLED", "intake": INTAKE_MANUAL},
    {"id": "doc-revoked-0b44", "displayName": "Laptop invoice", "category": "Purchase", "version": 1, "claimCount": 3,
     "status": "REVOKED", "provenanceLevel": "SELF_ENROLLED", "intake": INTAKE_PLAIN},
    {"id": "doc-old-a1f8", "displayName": "Semester 6 marksheet", "category": "Education", "version": 1, "claimCount": 6,
     "status": "SUPERSEDED", "provenanceLevel": "SELF_ENROLLED", "intake": INTAKE_PLAIN},
]

CATEGORIES = ("Education", "Employment", "Finance", "Identity", "Purchase", "Other")

CLAIMS = [
    {"id": "c1", "label": "Name", "value": "Ananya Rao", "type": "string", "path": "person.name"},
    {"id": "c2", "label": "Institution", "value": "Example Institute of Technology", "type": "string", "path": "education.institution"},
    {"id": "c3", "label": "Course", "value": "B.Tech Computer Science", "type": "string", "path": "education.course"},
    {"id": "c4", "label": "CGPA", "value": "9.17", "type": "decimal", "path": "education.cgpa"},
    {"id": "c5", "label": "CGPA at least 8.5", "value": "true", "type": "boolean", "path": "education.cgpa_at_least_8_5", "derivedFrom": "education.cgpa"},
    {"id": "c6", "label": "Date of birth", "value": "2004-03-18", "type": "date", "path": "person.birth_date"},
]


def home(query="", empty=False):
    docs = [] if empty else DOCUMENTS
    shown = [d for d in docs if query.lower() in d["displayName"].lower()]
    return dict(documents=shown, categories=CATEGORIES, category="", query=query, error=None,
                document_count=len(docs), active_count=sum(d["status"] == "ACTIVE" for d in docs),
                fact_count=sum(d["claimCount"] for d in docs))


def enroll():
    return dict(categories=CATEGORIES, previous_id=None, intake_folder=r"C:\Users\Example\Foliolet Intake", managed_intake=True,
                observations=[{"id": "obs-1", "filename": "marksheet_sem6.pdf", "receivedAt": "2026-10-16T09:12:00+05:30"}])


def detail(kind):
    if kind == "draft":
        doc = dict(DOCUMENTS[1])
        doc.update(claims=[], intake=dict(INTAKE_PLAIN, stage="Read locally. 5 suggested facts are ready for your review.",
                                          fields=[{"label": "Net pay", "value": "84,200", "type": "decimal", "citation": {"page": 1}, "evidence": "Net pay 84,200.00"},
                                                  {"label": "Employee ID", "value": "NW-20417", "type": "string", "citation": {"page": 1}, "evidence": "Emp. ID: NW-20417"}]))
        rows = [{"label": "Employer", "value": "Northwind Analytics Pvt. Ltd.", "type": "string", "path": "employment.employer", "citation": {"page": 1}, "evidence": "Northwind Analytics Pvt. Ltd."},
                {"label": "Net monthly pay", "value": "84200", "type": "decimal", "path": "employment.net_pay", "citation": {"page": 1, "provenance": "OCR transcription"}, "evidence": "Net pay 84,200.00"},
                {"label": "Pay period", "value": "2026-09-30", "type": "date", "path": "employment.period_end"}]
        return dict(document=doc, claim_rows=rows)
    doc = dict(DOCUMENTS[0] if kind == "active" else DOCUMENTS[5])
    doc.update(claims=CLAIMS if kind == "active" else CLAIMS[:3], merkleRoot=ROOT, contract=CONTRACT, anchorTx=TX, chainId=1337,
               anchoredAt="2026-10-15T18:40:00+05:30", previousId="doc-old-a1f8" if kind == "active" else None,
               intake=dict(doc["intake"], stage="Read locally. Facts were compared with the saved suggestions.", changes={"edited": 1, "added": 1, "removed": 0}),
               provenance={"explanation": "The enrolled bytes matched a file your paired agent recorded on 16 Oct 2026. This shows continuity, not issuer authenticity."} if kind == "active" else {})
    return dict(document=doc, claim_rows=[])


def compose():
    doc = dict(DOCUMENTS[0], claims=CLAIMS)
    return dict(document=doc, selected=["c5"], form={"verifier_label": "Acme internship team", "purpose": "Internship eligibility check"}, share_mode="local")


GRANTS_OPEN = [
    {"id": "g1", "verifierLabel": "Acme internship team", "purpose": "Internship eligibility check", "status": "ACTIVE", "documentName": "Semester 6 marksheet",
     "credentialId": "doc-active-31c9", "createdAt": "2026-10-16T10:05:00+05:30", "expiresAt": "2026-10-17T10:05:00+05:30", "oneTime": True, "views": 0},
    {"id": "g2", "verifierLabel": "Mr. Kulkarni (landlord)", "purpose": "Tenancy application: income above ₹60,000 per month", "status": "ACTIVE", "documentName": "PAN card",
     "credentialId": "doc-id-2c77", "createdAt": "2026-10-16T12:30:00+05:30", "expiresAt": "2026-10-23T12:30:00+05:30", "oneTime": False, "views": 2,
     "receipts": [{"verifiedAt": "2026-10-16T12:41:00+05:30", "result": "VERIFIED_RELEASE"}, {"verifiedAt": "2026-10-16T18:02:00+05:30", "result": "VERIFIED_RELEASE"}]},
]
GRANTS_CLOSED = [
    {"id": "g3", "verifierLabel": "Scholarship desk", "purpose": "Merit scholarship", "status": "CONSUMED", "documentName": "Semester 6 marksheet",
     "credentialId": "doc-active-31c9", "createdAt": "2026-10-10T09:00:00+05:30", "expiresAt": "2026-10-11T09:00:00+05:30", "oneTime": True, "views": 1},
    {"id": "g4", "verifierLabel": "Electronics store warranty", "purpose": "Warranty claim", "status": "CREDENTIAL_UNAVAILABLE", "documentName": "Laptop invoice",
     "credentialId": "doc-revoked-0b44", "createdAt": "2026-10-02T15:20:00+05:30", "expiresAt": "2026-10-09T15:20:00+05:30", "oneTime": False, "views": 0},
    {"id": "g5", "verifierLabel": "Gym membership", "purpose": "Age check", "status": "REVOKED", "documentName": None,
     "credentialId": "doc-id-2c77", "createdAt": "2026-09-28T08:00:00+05:30", "expiresAt": "2026-09-29T08:00:00+05:30", "oneTime": False, "views": 0},
]
EVENTS = [
    {"timestamp": "2026-10-16T12:41:00+05:30", "action": "PUBLIC_PROOF_RELEASED", "documentName": "PAN card", "credentialId": "doc-id-2c77"},
    {"timestamp": "2026-10-16T12:30:00+05:30", "action": "DISCLOSURE_CREATED", "documentName": "PAN card", "credentialId": "doc-id-2c77"},
    {"timestamp": "2026-10-15T18:40:00+05:30", "action": "CREDENTIAL_ANCHORED", "documentName": "Semester 6 marksheet", "credentialId": "doc-active-31c9"},
    {"timestamp": "2026-10-15T18:31:00+05:30", "action": "FACTS_CONFIRMED", "documentName": "Semester 6 marksheet", "credentialId": "doc-active-31c9"},
]


def sharing():
    return dict(open_grants=GRANTS_OPEN, closed_grants=GRANTS_CLOSED, events=EVENTS)


def share_ready():
    return dict(share={"shareUrl": "http://127.0.0.1:8001/verify/preview-token-not-real/", "disclosedCount": 1, "privateCount": 5,
                       "expiresAt": "2026-10-17T10:05:00+05:30"},
                terms={"verifier": "Acme internship team", "purpose": "Internship eligibility check", "one_time": True}, share_mode="local")


def integrity():
    return dict(paired=None,
                agents=[{"id": "agent-3f9c2a", "label": "Work laptop", "active": True}, {"id": "agent-77b1d0", "label": "Old desktop", "active": False}],
                observations=[{"filename": "marksheet_sem6.pdf", "receivedAt": "2026-10-16T09:12:00+05:30", "sha256": "4f2a9c7e1b3d5f6a8c0e2d4b6f8a1c3e5d7b9f0a2c4e6d8b0a1c3e5f7d9b2a4c"},
                              {"filename": "salary_slip_sep_2026_northwind_analytics_bengaluru.pdf", "receivedAt": "2026-10-15T20:40:00+05:30", "sha256": "9b1d3f5a7c9e0b2d4f6a8c1e3b5d7f9a0c2e4b6d8f1a3c5e7b9d0f2a4c6e8b1d"}])


def signature():
    return dict(document={"id": "doc-active-31c9", "displayName": "Semester 6 marksheet", "version": 2},
                inspection={"status": "SIGNATURE_PRESENT_TRUST_NOT_ESTABLISHED", "sourceSha256": "4f2a9c7e1b3d5f6a8c0e2d4b6f8a1c3e5d7b9f0a2c4e6d8b0a1c3e5f7d9b2a4c",
                            "checkedAt": "16 Oct 2026, 09:20 IST",
                            "signatures": [{"index": 1, "status": "DIGEST_INTACT_TRUST_UNKNOWN", "digestIntact": True, "signatureMathValid": True,
                                            "entireCurrentFile": True, "certificatePathTrusted": None, "signerCertificateSha256": "c0ffee00" * 8}]})


def api_stubs():
    """Fictional JSON for client-side scripts in the static preview."""
    analysis = {"state": "DONE", "stage": "Read locally. Facts were compared with the saved suggestions.",
                "indicator": "POSSIBLE_DIGILOCKER_FORMAT", "method": "WATCHER_ASSISTED", "lineage": "SUGGESTIONS_MODIFIED", "fields": [],
                "report": {"manifest": {"readablePages": 1, "totalPages": 1, "ocrPages": 0, "warnings": [], "pages": []},
                           "indicators": {"inspectedPages": 1, "totalPages": 1, "warnings": [], "pages": []}}}
    draft = dict(analysis, indicator="NO_DIGILOCKER_INDICATOR", method="MANUAL", lineage="SUGGESTIONS_UNMODIFIED",
                 stage="Read locally. 3 suggested facts are ready for your review.")
    return {
        "/ask-foli/api/documents/": [
            {"id": "wallet:doc-active-31c9", "name": "Semester 6 marksheet", "filename": "marksheet_sem6.pdf", "format": "pdf", "version": 2, "supported": True},
            {"id": "wallet:doc-draft-7f2a", "name": "Salary slip — September 2026", "filename": "salary_slip_sep_2026.pdf", "format": "pdf", "version": 1, "supported": True},
            {"id": "wallet:doc-ready-55e0", "name": "Rental agreement, Koramangala flat", "filename": "rental_agreement.png", "format": "png", "version": 1, "supported": False},
        ],
        "/ask-foli/api/health/": {"ollama": {"status": "READY", "model": "preview-model", "cloudDisabled": True}, "ocr": "local OCR"},
        "/intake/sessions/": {"sessions": [{"id": "s1", "active": True, "connected": True, "folder": r"C:\Users\Example\Foliolet Intake", "imported": 2}]},
        "/intake/files/": {"sessionId": "s1", "files": [
            {"relativePath": "marksheet_sem6.pdf", "name": "marksheet_sem6.pdf", "size": 184320, "modifiedAt": 1792130000000, "selection": "a"},
            {"relativePath": "salary_slip_sep_2026_northwind_analytics_bengaluru.pdf", "name": "salary_slip_sep_2026_northwind_analytics_bengaluru.pdf",
             "size": 96256, "modifiedAt": 1792040000000, "selection": "b"}]},
        "/intake/documents/doc-active-31c9/": analysis,
        "/intake/documents/doc-revoked-0b44/": dict(analysis, indicator="NO_DIGILOCKER_INDICATOR", method="MANUAL", lineage="SUGGESTIONS_UNMODIFIED"),
        "/intake/documents/doc-draft-7f2a/": draft,
    }


def verify(result):
    if not result:
        return dict(public=True, result=None, error=None)
    leaf = CLAIMS[4]
    bundle = {"credentialVersion": 2, "claims": [{"leaf": leaf}], "leafCount": 6, "format": "foliolet-selective-v1", "credentialId": "doc-active-31c9",
              "merkleRoot": ROOT, "envelopeHash": "0x" + "ab" * 32,
              "anchor": {"contract": CONTRACT, "operator": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266", "chainId": 1337, "txHash": TX, "anchoredAt": "2026-10-15T18:40:00+05:30"},
              "provenance": {"level": "FIRST_SEEN_TRACKED", "explanation": "The enrolled bytes matched an earlier record from the holder's own paired agent.", "firstReceivedAt": "2026-10-16T09:12:00+05:30", "observations": 1},
              "presentation": {"verifierLabel": "Acme internship team", "purpose": "Internship eligibility check", "createdAt": "2026-10-16T10:05:00+05:30",
                               "expiresAt": "2026-10-17T10:05:00+05:30", "oneTime": True, "grantId": "g1"}}
    verification = {"proofValid": True, "signatureValid": True, "anchorMatches": True, "current": True, "policyActive": True, "message": "All service checks passed."}
    return dict(public=True, result={"bundle": bundle, "verification": verification}, receiver_only=False, rpc_url="http://127.0.0.1:8545",
                network={"contract": CONTRACT, "operator": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266", "chainId": 1337})
