"""Real PostgreSQL + Spring HTTP + local EVM integration test. Creates isolated demo records.
Run from repository root after starting all services: .venv/Scripts/python tools/test-live-workflow.py
No mocks. Local filesystem damage tests always restore their own test files in finally blocks.
"""
import copy
import hashlib
import hmac
import json
import os
import re
from pathlib import Path
import struct
import subprocess
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import psycopg
import requests
from Crypto.Hash import keccak

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("WALLET_TEST_API", "http://127.0.0.1:8080")
DB = os.environ.get("WALLET_TEST_DSN", "host=127.0.0.1 port=55432 dbname=wallet_dev user=wallet")
assert BASE.startswith(("http://127.0.0.1:", "http://localhost:")), "Use isolated local services"
checks = []


def check(condition, name):
    assert condition, name
    checks.append(name)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] PASS {name}", flush=True)


def call(method, path, auth=None, expected=200, **kwargs):
    r = requests.request(method, BASE + path, auth=auth, timeout=(5, 70), **kwargs)
    assert r.status_code == expected, f"{method} {path}: {r.status_code} {r.text[:300]}"
    return r.json() if "application/json" in r.headers.get("Content-Type", "") else r.text


def account():
    name = "demo_" + uuid.uuid4().hex[:10]
    auth = (name, "local-demo-password-123")
    call("POST", "/api/auth/register", json={"username": name, "password": auth[1], "role": "HOLDER"})
    return auth


def upload(auth, content, observation=None, previous=None):
    path = f"/api/wallet/documents/{previous}/versions" if previous else "/api/wallet/documents"
    return call("POST", path, auth, files={"file": ("marksheet.txt", content, "text/plain")},
                data={"displayName": "Private marksheet", "category": "Education", "observationId": observation or ""})


def commit(auth, d):
    claims = d["suggestions"]
    check(len(claims) == 5, "deterministic extraction supplies five reviewable suggestions")
    confirmed = call("PUT", f"/api/wallet/documents/{d['id']}/claims", auth, json={"claims": claims})
    check(len(confirmed["claims"]) == 6, "platform computes the committed threshold boolean")
    active = call("POST", f"/api/wallet/documents/{d['id']}/anchor", auth)
    check(active["status"] == "ACTIVE" and active["anchorTx"].startswith("0x"), "real transaction anchors credential")
    return active


def share(auth, d, one_time=False):
    chosen = next(c for c in d["claims"] if c["path"] == "education.cgpa_at_least_8_5")
    return call("POST", "/api/wallet/disclosures", auth, json={"credentialId": d["id"], "claimIds": [chosen["id"]],
        "verifierLabel": "Scholarship desk", "purpose": "Check eligibility", "expiresInMinutes": 120, "oneTime": one_time})


def token_path(s):
    return "/api/public/disclosures/" + s["shareUrl"].rstrip("/").split("/")[-1] + "/open"


def observation(agent, item, content, sequence, previous):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    data = {"agentId": agent["agentId"], "itemId": item, "filename": "marksheet.txt", "sha256": hashlib.sha256(content).hexdigest(),
        "observedAt": now.isoformat().replace("+00:00", "Z"), "sequence": sequence, "previousDigest": previous}
    fields = ["first-seen-v1", data["agentId"], item, data["filename"], data["sha256"], str(int(now.timestamp())), str(sequence), previous]
    raw = b"".join(struct.pack(">I", len(v.encode())) + v.encode() for v in fields)
    data["signature"] = hmac.new(bytes.fromhex(agent["secret"][2:]), raw, hashlib.sha256).hexdigest()
    digest = "0x" + keccak.new(digest_bits=256, data=raw).hexdigest()
    return data, digest


def main():
    network = json.loads((ROOT / '.local-data/trusted-deployment.json').read_text(encoding='utf-8'))
    # Trust is provisioned independently. Spring discovery is only a consistency assertion.
    reported = call("GET", "/api/public/network")
    check(all(str(reported[k]).lower() == str(network[k]).lower() for k in ('contract', 'operator', 'chainId')),
          "Spring deployment matches separately provisioned local trust pins")
    owner, stranger = account(), account()
    call("GET", "/api/wallet/documents", expected=401)
    call("POST", "/api/auth/register", expected=400, json={"username": "admin_"+uuid.uuid4().hex[:8], "password": owner[1], "role": "ADMIN"})
    check(True, "wallet requires authentication and registration cannot grant ADMIN")
    original = b"Name: Hidden Demo Student\nCGPA: 9.17\nInstitution: Hidden Institute\nCourse: Computer Science\nDate of birth: 2004-01-02\n"
    agent = call("POST", "/api/wallet/integrity/agents", owner, json={"label": "Demo folder"})
    item = str(uuid.uuid4())
    report, digest = observation(agent, item, original, 1, "0x"+"00"*32)
    forged = dict(report, signature="00"*32)
    call("POST", "/api/integrity/observations", expected=401, json=forged)
    observed = call("POST", "/api/integrity/observations", json=report)
    check(observed["digest"] == digest, "authenticated observation agrees with independent Keccak encoding")
    check(call("POST", "/api/integrity/observations", json=report) == observed, "signed replay is idempotent")
    conflicting, _ = observation(agent, item, original+b"changed", 1, "0x"+"00"*32)
    call("POST", "/api/integrity/observations", expected=409, json=conflicting)
    check(True, "forged observation and conflicting sequence are rejected")
    call("POST", "/api/wallet/documents", stranger, expected=404,
         files={"file": ("marksheet.txt", original)}, data={"displayName": "Cross account", "category": "Education", "observationId": observed["observationId"]})
    d = commit(owner, upload(owner, original, observed["observationId"]))
    check(d["provenanceLevel"] == "FIRST_SEEN_TRACKED", "first-seen continuity is distinguished from self enrollment")
    call("GET", f"/api/wallet/documents/{d['id']}", stranger, expected=404)
    call("GET", f"/api/wallet/documents/{d['id']}/file", stranger, expected=404)
    check(True, "cross-account document and original access are rejected")
    s = share(owner, d)
    scanner = requests.get(BASE+token_path(s), timeout=10)
    check(scanner.status_code in (401, 405) and call("GET", f"/api/public/grants/{s['id']}/status")["views"] == 0,
          "GET/link scanner cannot release facts or consume a grant")
    opened = call("POST", token_path(s))
    bundle = opened["bundle"]
    check(opened["verification"]["verified"], "public release verifies current anchored commitment")
    raw = json.dumps(opened)
    check(len(bundle["claims"]) == 1 and bundle["claims"][0]["leaf"]["value"] == "true"
          and all(v not in raw for v in ("Hidden Demo Student", "Hidden Institute", "9.17", "2004-01-02")), "hidden values and original are absent from the public presentation")
    artifact = ROOT / ".local-data" / "live-test-proof.json"
    artifact.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    result = subprocess.run(["node", str(ROOT / "spring-boot-service/scripts/verify-proof.cjs"), str(artifact),
        "--contract", network["contract"], "--operator", network["operator"], "--chain-id", str(network["chainId"])], capture_output=True, text=True)
    check(result.returncode == 0, "separate Node verifier recomputes Merkle/signature and reads actual EVM state")
    mutations = {
        "value": lambda b: b["claims"][0]["leaf"].update(value="false"),
        "salt": lambda b: b["claims"][0]["leaf"].update(salt="0x"+"00"*32),
        "path": lambda b: b["claims"][0]["leaf"].update(path="education.other"),
        "proof sibling": lambda b: b["claims"][0]["proof"][0].update(sibling="0x"+"00"*32),
        "root": lambda b: b.update(merkleRoot="0x"+"00"*32),
        "purpose": lambda b: b["presentation"].update(purpose="Different purpose"),
        "expiry": lambda b: b["presentation"].update(expiresAt="2099-01-01T00:00:00Z"),
        "provenance": lambda b: b["provenance"].update(level="ISSUER_VERIFIED"),
        "network": lambda b: b["anchor"].update(chainId=1),
    }
    for label, mutate in mutations.items():
        changed = copy.deepcopy(bundle)
        mutate(changed)
        rejected = call("POST", "/api/public/verify-bundle", json=changed)
        check(not rejected["verified"], f"tampered {label} cannot pass verification")
    one = share(owner, d, True)
    def open_status(_):
        return requests.post(BASE+token_path(one), timeout=70).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = sorted(pool.map(open_status, range(2)))
    check(statuses == [200, 410], "concurrent one-time release is atomic in PostgreSQL")
    call("POST", f"/api/wallet/disclosures/{s['id']}/revoke", owner)
    call("POST", token_path(s), expected=410)
    check(not call("POST", "/api/public/verify-bundle", json=bundle)["verified"], "revoked service link and policy verification reject further release")
    expires = share(owner, d)
    with psycopg.connect(DB) as db:
        db.execute("UPDATE disclosure_grants SET expires_at = now() - interval '1 second' WHERE id = %s", (expires["id"],))
    call("POST", token_path(expires), expected=410)
    check(True, "expired grant rejects release (test changes only its own disposable row)")
    with psycopg.connect(DB) as db:
        file_path, backup_path = db.execute("SELECT file_path, backup_path FROM wallet_documents WHERE id=%s", (d["id"],)).fetchone()
    if not Path(file_path).is_absolute():
        file_path = ROOT / "spring-boot-service" / file_path
        backup_path = ROOT / "spring-boot-service" / backup_path
    file_path, backup_path = Path(file_path), Path(backup_path)
    allowed = (ROOT / ".local-data" / "wallet").resolve()
    check(file_path.resolve().is_relative_to(allowed) and backup_path.resolve().is_relative_to(allowed), "damage test targets only its isolated wallet files")
    cipher, backup = file_path.read_bytes(), backup_path.read_bytes()
    check(original not in cipher, "private original is encrypted at rest")
    try:
        file_path.write_bytes(cipher[:-1]+bytes([cipher[-1]^1]))
        broken = call("POST", f"/api/wallet/documents/{d['id']}/integrity", owner)
        check(not broken["intact"], "AES/document commitment detects damaged private file")
        call("POST", "/api/wallet/disclosures", owner, expected=409, json={"credentialId": d["id"], "claimIds": [d["claims"][0]["id"]], "verifierLabel": "Desk", "purpose": "Check", "expiresInMinutes": 5, "oneTime": False})
        recovered = call("POST", f"/api/wallet/documents/{d['id']}/integrity?restore=true", owner)
        check(recovered["restored"] and not recovered["intact"], "valid backup is checked against anchor before recovery")
        file_path.write_bytes(cipher[:-1]+bytes([cipher[-1]^1]))
        backup_path.write_bytes(backup[:-1]+bytes([backup[-1]^1]))
        check(not call("POST", f"/api/wallet/documents/{d['id']}/integrity?restore=true", owner)["restored"], "corrupt backup is never installed")
    finally:
        file_path.write_bytes(cipher)
        backup_path.write_bytes(backup)
    changed_report, digest2 = observation(agent, item, original+b"changed", 2, digest)
    changed_obs = call("POST", "/api/integrity/observations", json=changed_report)
    changed_doc = upload(owner, original, changed_obs["observationId"])
    check(changed_doc["provenanceLevel"] == "SELF_ENROLLED" and changed_doc["provenance"]["observedChanges"], "observed change prevents continuity upgrade")
    call("POST", f"/api/wallet/integrity/agents/{agent['agentId']}/revoke", owner)
    revoked_report, _ = observation(agent, item, original, 3, digest2)
    call("POST", "/api/integrity/observations", expected=401, json=revoked_report)
    check(True, "revoked paired agent cannot submit new observations")
    old_share = share(owner, d)
    old_bundle = call("POST", token_path(old_share))["bundle"]
    newer = commit(owner, upload(owner, original.replace(b"9.17", b"9.25"), previous=d["id"]))
    check(newer["version"] == 2 and call("GET", f"/api/wallet/documents/{d['id']}", owner)["status"] == "SUPERSEDED", "real new anchor supersedes old immutable credential")
    check(not call("POST", "/api/public/verify-bundle", json=old_bundle)["verified"], "old proof fails latest chain state after supersession")
    call("POST", token_path(old_share), expected=409)
    next_share = share(owner, newer)
    next_bundle = call("POST", token_path(next_share))["bundle"]
    call("POST", f"/api/wallet/documents/{newer['id']}/revoke", owner)
    check(not call("POST", "/api/public/verify-bundle", json=next_bundle)["verified"], "credential revocation is independently visible on chain")
    # Retain a fresh, usable browser/demo fixture. No tampered data is used in this account's active credential.
    demo = commit(owner, upload(owner, original))
    demo_share = share(owner, demo)
    session = {"username": owner[0], "password": owner[1], "documentId": demo["id"], "share": demo_share, "network": network}
    (ROOT / ".local-data" / "demo-session.json").write_text(json.dumps(session), encoding="utf-8")
    receipt = call("GET", "/api/wallet/disclosures", owner)
    check(any(g["receipts"] for g in receipt), "holder activity includes verified release receipts")
    live_agent = call("POST", "/api/wallet/integrity/agents", owner, json={"label": "CLI watcher test"})
    watcher_dir = ROOT / ".local-data" / ("watcher-test-"+uuid.uuid4().hex[:8])
    intake = watcher_dir / "intake" / "nested"
    intake.mkdir(parents=True)
    source = intake / "marksheet.txt"
    source.write_bytes(original)
    config = watcher_dir / "agent.json"
    config.write_text(json.dumps(dict(live_agent, apiUrl=BASE)), encoding="utf-8")
    watcher_cmd = [sys.executable, str(ROOT / "tools/local-watcher/watch.py"), str(intake.parent), "--config", str(config), "--once"]
    first = subprocess.run(watcher_cmd, capture_output=True, text=True)
    again = subprocess.run(watcher_cmd, capture_output=True, text=True)
    check(first.returncode == again.returncode == 0, "real recursive watcher resumes its signed persisted state without duplicate reports")
    source.write_bytes(original+b"Observed change")
    changed_run = subprocess.run(watcher_cmd, capture_output=True, text=True)
    obs = [o for o in call("GET", "/api/wallet/integrity/observations", owner) if o["agentId"] == live_agent["agentId"]]
    check(changed_run.returncode == 0 and len(obs) == 2 and len({o["itemId"] for o in obs}) == 1,
          "real watcher records a changed nested file with stable identity and sequence")
    legacy = call("POST", "/api/documents", owner, files={"file": ("compatibility.txt", b"Legacy integrity regression")},
                  data={"caseId": "LOCAL-COMPATIBILITY-TEST", "documentType": "OTHER"})
    legacy_check = call("GET", f"/api/documents/{legacy['documentId']}/verify", owner)
    check(not legacy_check["tampered"], "preserved legacy upload anchors and verifies through original Solidity registry")
    ui_share = share(owner, demo, True)
    ui = requests.Session()
    landing = ui.get(ui_share["shareUrl"], timeout=20)
    csrf = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', landing.text).group(1)
    released = ui.post(ui_share["shareUrl"], data={"csrfmiddlewaretoken": csrf}, headers={"Origin": "http://localhost:8000"}, timeout=70)
    check(released.status_code == 200 and "Service verification passed" in released.text, "real Django CSRF-protected one-time release succeeds")
    export_url = "http://localhost:8000/proof-download/"+ui_share["id"]+"/"
    exported = ui.get(export_url, timeout=70)
    check(exported.status_code == 200 and "attachment" in exported.headers.get("Content-Disposition", "")
          and len(exported.json()["claims"]) == 1 and "9.17" not in exported.text, "real HTTP attachment exports only the already released fact/proof")
    check(call("GET", f"/api/public/grants/{ui_share['id']}/status")["views"] == 1, "downloading the released proof does not reconsume the one-time grant")
    check(requests.get(export_url, timeout=10).status_code == 404, "a different browser session cannot export the retained presentation")
    call("POST", f"/api/wallet/disclosures/{ui_share['id']}/revoke", owner)
    check(ui.get(export_url, timeout=70).status_code == 410, "revoked cached export fails current-policy check without disclosing facts")
    report = {"completedAt": datetime.now(timezone.utc).isoformat(), "checks": checks, "network": network,
              "count": len(checks), "transport": "real HTTP/PostgreSQL/Ganache/Web3j"}
    (ROOT / ".local-data" / "live-test-results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Completed {len(checks)} checks. Demo credentials: .local-data/demo-session.json", flush=True)


if __name__ == "__main__":
    main()
