"""Presentation vocabulary from DESIGN.md §10. Display only: never feeds a security decision."""
from django import template

register = template.Library()

GRANT_STATES = {
    "ACTIVE": ("Open", "pass"),
    "CONSUMED": ("Used (one-time)", "quiet"),
    "EXPIRED": ("Expired", "quiet"),
    "REVOKED": ("Revoked", "fail"),
    "CREDENTIAL_UNAVAILABLE": ("Source credential no longer current", "caution"),
}

EVENTS = {
    "DOCUMENT_ENROLLED": "Document enrolled",
    "FACTS_CONFIRMED": "Facts confirmed",
    "CREDENTIAL_ANCHORED": "Commitment anchored",
    "CREDENTIAL_REVOKED": "Credential revoked",
    "DISCLOSURE_CREATED": "Proof link created",
    "DISCLOSURE_REVOKED": "Proof link revoked",
    "PUBLIC_PROOF_RELEASED": "Facts released to a verifier",
    "INTEGRITY_AGENT_PAIRED": "First-seen agent paired",
    "INTEGRITY_AGENT_REVOKED": "First-seen agent revoked",
    "FILE_INTEGRITY_CHECKED": "Private file checked: intact",
    "FILE_INTEGRITY_MISMATCH": "Private file checked: mismatch found",
    "INTEGRITY_RESTORED": "Private file recovered",
}


@register.filter
def doc_state(doc):
    """(label, tone, next action) for a document summary or detail."""
    status = (doc or {}).get("status")
    if status == "DRAFT":
        confirmed = doc.get("merkleRoot") or doc.get("claimCount")
        return ("Ready to anchor", "seal", "Anchor") if confirmed else ("Needs fact review", "caution", "Review facts")
    return {
        "ANCHOR_PENDING": ("Anchoring incomplete", "caution", "Retry anchor"),
        "ACTIVE": ("Anchored · shareable", "pass", "Share a proof"),
        "REVOKED": ("Revoked", "fail", "View"),
        "SUPERSEDED": ("Replaced by newer version", "quiet", "View"),
    }.get(status, (status or "Unknown", "quiet", "View"))


@register.filter
def lifecycle(doc):
    """Steps for the lifecycle line: list of (label, state) with state in done/now/todo/stopped/retired."""
    status = (doc or {}).get("status")
    has_facts = bool(doc.get("merkleRoot") or doc.get("claims"))
    if status == "DRAFT":
        return [("Uploaded", "done"), ("Facts confirmed", "done" if has_facts else "now"),
                ("Anchored", "now" if has_facts else "todo"), ("Shareable", "todo")]
    if status == "ANCHOR_PENDING":
        return [("Uploaded", "done"), ("Facts confirmed", "done"), ("Anchoring", "now"), ("Shareable", "todo")]
    last = {"ACTIVE": ("Shareable", "now"), "REVOKED": ("Revoked", "stopped"),
            "SUPERSEDED": ("Superseded", "retired")}.get(status, (status or "Unknown", "todo"))
    return [("Uploaded", "done"), ("Facts confirmed", "done"), ("Anchored", "done"), last]


@register.filter
def grant_state(status):
    return GRANT_STATES.get(status, (status or "Unknown", "quiet"))


@register.filter
def event_label(action):
    return EVENTS.get(action, (action or "").replace("_", " ").capitalize())


@register.filter
def redactions(count):
    """Stable width classes for `count` redaction bars (position-derived, never random)."""
    try:
        count = max(0, int(count))
    except (TypeError, ValueError):
        return []
    return [f"w{(i * 5 + 2) % 6 + 1}" for i in range(count)]


@register.filter
def withheld(bundle):
    """Committed facts not disclosed in a proof bundle (leafCount is already public in the bundle)."""
    try:
        return max(0, int(bundle["leafCount"]) - len(bundle["claims"]))
    except (TypeError, ValueError, KeyError):
        return 0


@register.filter
def first_seen(level):
    return level == "FIRST_SEEN_TRACKED"


_ASSET_VERSIONS = {}


@register.simple_tag
def asset(path):
    """Static URL with a content hash, so a redesigned stylesheet or script is never served stale."""
    from hashlib import sha256
    from django.contrib.staticfiles import finders
    from django.templatetags.static import static
    from django.conf import settings
    if path not in _ASSET_VERSIONS or settings.DEBUG:
        found = finders.find(path)
        try:
            with open(found, "rb") as handle:
                _ASSET_VERSIONS[path] = sha256(handle.read()).hexdigest()[:12]
        except (TypeError, OSError):
            _ASSET_VERSIONS[path] = ""
    version = _ASSET_VERSIONS[path]
    return static(path) + (f"?v={version}" if version else "")
