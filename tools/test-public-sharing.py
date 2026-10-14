"""Real HTTPS receiver acceptance with synthetic data. No bearer paths in output.

Run with isolated original Foliolet PostgreSQL/Spring/EVM/private Django services.
This intentionally stops/restarts this checkout's Quick Tunnel. No physical
second device is implied: the HTTPS client runs on the holder's computer.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
from zoneinfo import ZoneInfo
import psycopg
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "django-service"))
from dashboard import tunnel_manager as tunnel

UI = "http://localhost:8000"
API = "http://127.0.0.1:8080"
DSN = "host=127.0.0.1 port=55432 dbname=wallet_dev user=wallet"
events = []


def check(ok, name, response=None, origin=None):
    assert ok, name  # Never include response bodies or bearer URLs in failures.
    record = {"test": name, "result": "PASS", "time": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()}
    if response is not None:
        record["httpStatus"] = response.status_code
    if origin:
        record["origin"] = origin  # Hostname only, never a bearer route.
    events.append(record)
    print("[%s] PASS %s%s" % (record["time"], name,
          " HTTP %s" % record["httpStatus"] if "httpStatus" in record else ""), flush=True)


def csrf(response):
    found = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)
    assert found, "CSRF form token exists"
    return found.group(1)


def call(method, path, auth=None, **kwargs):
    response = requests.request(method, API+path, auth=auth, timeout=(3, 70), **kwargs)
    assert response.status_code == 200, "Synthetic internal API operation succeeds"
    return response.json() if "application/json" in response.headers.get("Content-Type", "") else response.text


def holder(auth):
    session = requests.Session()
    landing = session.get(UI+"/login/", timeout=10)
    response = session.post(UI+"/login/", data={"username": auth[0], "password": auth[1],
        "csrfmiddlewaretoken": csrf(landing)}, headers={"Origin": UI}, timeout=15)
    assert response.status_code == 200 and "Signed in as" in response.text, "Holder login succeeds"
    return session


def create(session, doc, claim, one_time=False):
    path = "/wallet/"+doc+"/share/"
    composer = session.get(UI+path, timeout=10)
    response = session.post(UI+path, data={"claims": claim, "expires_minutes": "30",
        "verifier_label": "Synthetic receiver", "purpose": "Tunnel acceptance",
        "one_time": "yes" if one_time else "", "csrfmiddlewaretoken": csrf(composer)},
        headers={"Origin": UI}, timeout=(3, 90))
    found = re.search(r'id="share-url" value="([^"]+)"', response.text)
    assert found, "Holder publishes an actual verified public share URL"
    url = found.group(1)
    origin = "https://" + requests.utils.urlparse(url).netloc
    tunnel.validate_origin(origin)
    assert re.fullmatch(r"/verify/[0-9a-f]{64}/", requests.utils.urlparse(url).path), "Public bearer route is exact"
    grants = call("GET", "/api/wallet/disclosures", session.auth)
    return {"url": url, "origin": origin, "grant": grants[0]["id"], "receipt": response}


def receiver(share):
    session = requests.Session()
    response = session.get(share["url"], timeout=15)
    assert response.status_code == 200, "Public landing responds"
    return session, response


def open_facts(session, share, landing):
    return session.post(share["url"], data={"csrfmiddlewaretoken": csrf(landing)},
                        headers={"Origin": share["origin"]}, timeout=(3, 70))


def main():
    assert tunnel.config()["mode"] == "quick", "Acceptance runs only a Quick Tunnel"
    try:
        tunnel.stop_public()
    except tunnel.TunnelError:
        pass
    auth = ("cf_"+secrets.token_hex(6), "synthetic-"+secrets.token_hex(10))
    call("POST", "/api/auth/register", json={"username": auth[0], "password": auth[1], "role": "HOLDER"})
    source = b"Name: Hidden Tunnel Student\nCGPA: 9.17\nInstitution: Hidden Tunnel College\nCourse: Computing\nDate of birth: 2004-01-02\n"
    doc = call("POST", "/api/wallet/documents", auth, files={"file": ("synthetic.txt", source, "text/plain")},
               data={"displayName": "Synthetic Tunnel Marksheet", "category": "Education"})
    doc = call("PUT", "/api/wallet/documents/"+doc["id"]+"/claims", auth, json={"claims": doc["suggestions"]})
    doc = call("POST", "/api/wallet/documents/"+doc["id"]+"/anchor", auth)
    claim = next(c["id"] for c in doc["claims"] if c["path"] == "education.cgpa_at_least_8_5")
    owner = holder(auth)
    owner.auth = auth
    first = create(owner, doc["id"], claim, one_time=True)
    active = tunnel.rpc("status", tunnel.config())
    check(active["state"] == "ready" and active["tunnelPid"], "First holder share automatically starts receiver and tunnel", first["receipt"], first["origin"])
    check('value="'+first["url"]+'"' in first["receipt"].text and 'href="'+first["url"]+'"' in first["receipt"].text,
          "Receipt and preview contain the exact same HTTPS public URL")
    check("Temporary public HTTPS link" in first["receipt"].text, "Quick hostname lifetime is prominent")
    peer, landing = receiver(first)
    check("Nothing has been released yet" in landing.text and "Hidden Tunnel" not in landing.text,
          "Real public HTTPS GET reveals no fact values", landing, first["origin"])
    head = peer.head(first["url"], timeout=15)
    check(head.status_code == 200 and not head.content, "Real public HEAD reveals nothing", head)
    grants = call("GET", "/api/wallet/disclosures", auth)
    check(next(g for g in grants if g["id"] == first["grant"])["views"] == 0, "GET and HEAD have not consumed the grant")
    for private in ("/", "/admin/", "/login/", "/register/", "/wallet/", "/sharing/", "/integrity/", "/api/", "/api/public/network", "/legacy/", "/.local-data/", "/status", "/static/admin/js/core.js"):
        blocked = peer.get(first["origin"]+private, timeout=15)
        check(blocked.status_code in (403,404), "Public private route blocked: "+private, blocked)
    assets = re.findall(r'(?:src|href)="(/static/[^\"]+)"', landing.text)
    for asset in sorted(set(assets)):
        loaded = peer.get(first["origin"]+asset, timeout=15)
        check(loaded.status_code == 200, "Public static asset loads: "+asset.split("?")[0], loaded)
    check(landing.headers.get("Cache-Control") == "no-store, private" and
          landing.headers.get("Referrer-Policy") == "strict-origin" and
          landing.headers.get("Strict-Transport-Security") == "max-age=3600" and
          "connect-src 'self';" in landing.headers.get("Content-Security-Policy", ""), "Public sensitive headers and CSP enforced")
    check("Secure" in landing.headers.get("Set-Cookie", "") and "HttpOnly" in landing.headers.get("Set-Cookie", "") and
          "SameSite=Lax" in landing.headers.get("Set-Cookie", ""), "Real HTTPS CSRF cookie is secure HttpOnly SameSite=Lax")
    invalid = peer.post(first["url"], data={"csrfmiddlewaretoken": csrf(landing)}, headers={"Origin": "https://evil.example"}, timeout=15)
    check(invalid.status_code == 403 and "Service verification passed" not in invalid.text, "Public forged Origin denied before release", invalid)
    spoof = peer.get(first["url"], headers={"Host": "other.trycloudflare.com"}, timeout=15)
    check(spoof.status_code in (400,403,404,530), "Public forged Host denied", spoof)
    two = [receiver(first) for _ in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        releases = list(pool.map(lambda pair: open_facts(pair[0], first, pair[1]), two))
    good = [i for i,r in enumerate(releases) if "Service verification passed" in r.text]
    check(len(good) == 1, "Two simultaneous real public POSTs release one-time facts exactly once")
    released = releases[good[0]]
    check("education.cgpa_at_least_8_5" in released.text and all(secret not in released.text for secret in
          ("9.17", "Hidden Tunnel Student", "Hidden Tunnel College", "2004-01-02")), "Public release includes only authorized threshold", released)
    check('id="rpc-url"' not in released.text and 'id="verify-independent"' not in released.text and
          '127.0.0.1' not in released.text and 'localhost' not in released.text, "Public page has no direct loopback RPC and explains independent-check limitation")
    winner = two[good[0]][0]
    download_path = "/proof-download/"+first["grant"]+"/"
    downloaded = winner.get(first["origin"]+download_path, timeout=15)
    check(downloaded.status_code == 200 and downloaded.json()["claims"][0]["leaf"]["value"] == "true", "Public session-bound proof export succeeds", downloaded)
    check(requests.get(first["origin"]+download_path, timeout=15).status_code == 404, "Different public session cannot export released proof")
    repeated = open_facts(peer, first, landing)
    check("Service verification passed" not in repeated.text and "can't be opened" in repeated.text, "Second one-time POST is denied", repeated)
    # Separate private sessions exercise startup coordination in two request workers.
    holders = [holder(auth) for _ in range(2)]
    for s in holders:
        s.auth = auth
    with ThreadPoolExecutor(max_workers=2) as pool:
        shares = list(pool.map(lambda s: create(s, doc["id"], claim), holders))
    # Parallel list order is not identity; locate each grant from the backend token hash.
    with psycopg.connect(DSN) as db:
        import hashlib
        for share in shares:
            token = requests.utils.urlparse(share["url"]).path.split("/")[2]
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            share["grant"] = db.execute("SELECT id FROM disclosure_grants WHERE token_hash=%s", (token_hash,)).fetchone()[0]
    now = tunnel.rpc("status", tunnel.config())
    check(all(s["origin"] == first["origin"] for s in shares) and now["tunnelPid"] == active["tunnelPid"], "Two simultaneous holder shares reuse exactly one tunnel and origin")
    call("POST", "/api/wallet/disclosures/"+shares[0]["grant"]+"/revoke", auth)
    revoked_peer, revoked_landing = receiver(shares[0])
    denial = open_facts(revoked_peer, shares[0], revoked_landing)
    check("Service verification passed" not in denial.text, "Revocation denies future public releases", denial)
    with psycopg.connect(DSN) as db:
        db.execute("UPDATE disclosure_grants SET expires_at=now()-interval '1 second' WHERE id=%s", (shares[1]["grant"],))
    expired_peer, expired_landing = receiver(shares[1])
    denial = open_facts(expired_peer, shares[1], expired_landing)
    check("Service verification passed" not in denial.text, "Expired synthetic grant denies public release", denial)
    # Process death is deliberate and limited to the PID authenticated by this owner.
    subprocess.run(["taskkill", "/PID", str(now["tunnelPid"]), "/F"], capture_output=True, check=True, timeout=10) if sys.platform == "win32" else __import__("os").kill(now["tunnelPid"], 15)
    time.sleep(0.3)
    check(tunnel.rpc("status", tunnel.config())["state"] == "unavailable", "Dead tunnel status cannot advertise a ready public origin")
    fresh = create(owner, doc["id"], claim)
    check(fresh["origin"] != first["origin"], "New holder share recovers dead tunnel using a newly verified hostname", fresh["receipt"], fresh["origin"])
    fresh_peer, fresh_landing = receiver(fresh)
    check("Service verification passed" in open_facts(fresh_peer, fresh, fresh_landing).text, "Recovered public hostname completes selective release")
    retained = {"username": auth[0], "password": auth[1], "documentId": doc["id"], "claimId": claim,
                "publicOrigin": fresh["origin"]}
    (ROOT/".local-data/cloudflare-demo.json").write_text(json.dumps(retained), encoding="utf-8")
    (ROOT/".local-data/cloudflare-public-results.json").write_text(json.dumps({
        "clientNetwork": "HTTPS requests on the holder computer through the actual Cloudflare edge",
        "physicalCellularDevice": "NOT_TESTED: no second physical device available to this agent",
        "expiryFixture": "Only this test's grant expiry is moved into the past in isolated PostgreSQL",
        "events": events}, indent=2), encoding="utf-8")
    print("Completed %d real public HTTPS checks. Tokens omitted; physical cellular device NOT TESTED." % len(events), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Requests exceptions contain URLs. Print only a safe test label/type.
        print("FAIL: " + (str(exc) if isinstance(exc, AssertionError) else type(exc).__name__), file=sys.stderr)
        sys.exit(1)
