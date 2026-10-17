"""Receiver profile/security, publication and supervisor failure regressions."""
import io
import os
from pathlib import Path
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch
from django.http import HttpResponse
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from hermes import receiver_settings
from . import tunnel_manager as tunnel
from .receiver_surface import ReceiverBoundaryMiddleware
from .test_security import bundle, passed

ORIGIN = "https://unit-receiver.trycloudflare.com"
HOST = "unit-receiver.trycloudflare.com"
TOKEN = "a" * 64
PATH = "/verify/" + TOKEN + "/"
SNAPSHOT = {"mode": "quick", "origin": ORIGIN, "instance": "unit", "state": "ready"}
PROFILE = {key: getattr(receiver_settings, key) for key in (
    "ROOT_URLCONF", "MIDDLEWARE", "ALLOWED_HOSTS", "RECEIVER_ONLY", "PUBLIC_EVM_RPC_URL",
    "SESSION_COOKIE_NAME", "CSRF_COOKIE_NAME", "SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE",
    "SESSION_COOKIE_HTTPONLY", "CSRF_COOKIE_HTTPONLY", "SESSION_COOKIE_SAMESITE",
    "CSRF_COOKIE_SAMESITE", "CSRF_FAILURE_VIEW", "SECURE_PROXY_SSL_HEADER", "CSRF_TRUSTED_ORIGINS")}
PROFILE.update(DEBUG=False, PUBLIC_RECEIVER_ORIGIN=ORIGIN, PUBLIC_RECEIVER_INSTANCE="unit")


@override_settings(**PROFILE)
class ReceiverTests(TestCase):
    @patch("dashboard.wallet_views.api.call")
    def test_signed_selected_status_renders_only_after_full_verification(self, api):
        proof = bundle()
        proof['intakeStatus'] = {'schema': 'intake-status-v1', 'qr': 'PASSED', 'branding': 'PASSED',
            'imported': 'NOT_CHECKED', 'pdfSignature': 'NOT_APPLICABLE', 'issuer': 'UNVERIFIED',
            'facts': [{'index': 0, 'lineage': 'EDITED', 'support': 'REVIEW_REQUIRED'}]}
        api.return_value = {'bundle': proof, 'verification': passed()}
        response = self.client.post(PATH, secure=True, HTTP_HOST=HOST)
        self.assertContains(response, 'Holder edited this suggestion')
        self.assertContains(response, 'Original suggestion required source review')
        self.assertContains(response, 'DigiLocker-associated QR detected')
        self.assertContains(response, 'Issuer not verified')
        self.assertNotContains(response, 'Imported with Foliolet')
        api.return_value = {'bundle': proof, 'verification': passed() | {'verified': False}}
        response = self.client.post(PATH, secure=True, HTTP_HOST=HOST)
        self.assertNotContains(response, 'DigiLocker-associated QR detected')
        self.assertNotContains(response, 'Holder edited this suggestion')

    def get(self, path, **kwargs):
        return self.client.get(path, secure=True, HTTP_HOST=HOST, **kwargs)

    @patch("dashboard.wallet_views.api.call")
    def test_get_head_and_prefetch_never_release(self, api):
        for method in ("get", "head"):
            response = getattr(self.client, method)(PATH, secure=True, HTTP_HOST=HOST,
                                                  HTTP_SEC_PURPOSE="prefetch")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Cache-Control"], "no-store, private")
        response = self.get(PATH)
        self.assertContains(response, "Open disclosed facts")
        for private in ('href="/"', '/login/', '/register/', 'href="/wallet/', '/sharing/', '127.0.0.1', 'localhost'):
            self.assertNotContains(response, private)
        api.assert_not_called()

    def test_private_routes_and_invalid_tokens_are_absent(self):
        for path in ("/", "/admin/", "/login/", "/register/", "/wallet/", "/wallet/x/file/",
                     "/sharing/", "/integrity/", "/api/", "/api/public/network", "/legacy/",
                     "/verify/short/", "/verify/" + "A"*64 + "/", "/verify/" + TOKEN):
            self.assertEqual(self.get(path).status_code, 404, path)

    @patch("dashboard.wallet_views.api.call")
    def test_exact_host_https_and_methods(self, api):
        for host in ("other.trycloudflare.com", "evil.example", HOST + ":443", HOST + ".", "127.0.0.1:8001"):
            self.assertEqual(self.client.get(PATH, secure=True, HTTP_HOST=host).status_code, 400)
        self.assertEqual(self.client.get(PATH, HTTP_HOST=HOST, HTTP_X_FORWARDED_PROTO="https").status_code, 403)
        self.assertEqual(self.client.put(PATH, secure=True, HTTP_HOST=HOST).status_code, 405)
        api.assert_not_called()

    @patch("dashboard.wallet_views.api.call")
    def test_csrf_origin_and_real_profile_cookies(self, api):
        client = Client(enforce_csrf_checks=True)
        landing = client.get(PATH, secure=True, HTTP_HOST=HOST)
        csrf = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', landing.content.decode()).group(1)
        cookie = landing.cookies[receiver_settings.CSRF_COOKIE_NAME]
        self.assertTrue(cookie["secure"])
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(cookie["path"], "/")
        self.assertFalse(cookie["domain"])
        for origin in ("https://evil.example", "https://other.trycloudflare.com", "null", "http://"+HOST):
            response = client.post(PATH, {"csrfmiddlewaretoken": csrf}, secure=True,
                                   HTTP_HOST=HOST, HTTP_ORIGIN=origin)
            self.assertEqual(response.status_code, 403)
            self.assertNotIn(TOKEN, response.content.decode())
        self.assertEqual(client.post(PATH, secure=True, HTTP_HOST=HOST).status_code, 403)
        api.assert_not_called()
        api.return_value = {"bundle": bundle(), "verification": passed()}
        released = client.post(PATH, {"csrfmiddlewaretoken": csrf}, secure=True,
                               HTTP_HOST=HOST, HTTP_ORIGIN=ORIGIN)
        self.assertContains(released, "Service verification passed")
        self.assertContains(released, "independent browser chain checking is disabled")
        self.assertNotContains(released, 'id="verify-independent"')
        self.assertNotContains(released, 'id="rpc-url"')
        self.assertNotContains(released, '127.0.0.1')
        self.assertNotContains(released, 'ethers.umd')
        session_cookie = released.cookies[receiver_settings.SESSION_COOKIE_NAME]
        self.assertTrue(session_cookie["secure"])
        self.assertTrue(session_cookie["httponly"])
        self.assertEqual(session_cookie["samesite"], "Lax")
        api.assert_called_once_with("POST", "/api/public/disclosures/" + TOKEN + "/open")

    @patch("dashboard.wallet_views.api.call")
    def test_status_download_and_owner_cookie_are_session_bound(self, api):
        grant = bundle()["presentation"]["grantId"]
        self.client.cookies["sessionid"] = "private-owner-session"
        for route in ("proof-status", "proof-download"):
            self.assertEqual(self.get("/" + route + "/" + grant + "/").status_code, 404)
        api.assert_not_called()
        api.return_value = {"bundle": bundle(), "verification": passed()}
        self.client.post(PATH, secure=True, HTTP_HOST=HOST)
        api.return_value = {"status": "CONSUMED"}
        self.assertEqual(self.get("/proof-status/" + grant + "/").json()["status"], "CONSUMED")
        api.return_value = passed()
        self.assertEqual(self.get("/proof-download/" + grant + "/").json(), bundle())
        api.return_value = passed() | {"verified": False}
        self.assertEqual(self.get("/proof-download/" + grant + "/").status_code, 410)

    def test_static_allowlist_and_headers(self):
        for asset in ("theme.js", "wallet.js", "wallet.css", "verify.js", "fonts/public-sans-var.woff2"):
            response = self.get("/static/wallet/" + asset)
            self.assertEqual(response.status_code, 200)
            self.assertIn("connect-src 'self';", response["Content-Security-Policy"])
            self.assertEqual(response["Referrer-Policy"], "strict-origin")
            response.close()
        for path in ("/static/admin/js/core.js", "/static/../hermes/settings.py", "/static/wallet/vendor/ethers.umd.min.js",
                     "/static/wallet/fonts/LICENSES.md", "/static/wallet/wallet.css/../settings.py"):
            self.assertEqual(self.get(path).status_code, 404)

    def test_body_limits_and_rate_limiting(self):
        self.assertEqual(self.client.post(PATH, data=b"x"*17000, content_type="text/plain",
                                         secure=True, HTTP_HOST=HOST).status_code, 413)
        middleware = ReceiverBoundaryMiddleware(lambda request: HttpResponse())
        factory = RequestFactory()
        request = factory.get(PATH, secure=True, HTTP_HOST=HOST, HTTP_CF_CONNECTING_IP="198.51.100.1")
        for _ in range(90):
            self.assertEqual(middleware(request).status_code, 200)
        denied = middleware(request)
        self.assertEqual(denied.status_code, 429)
        self.assertEqual(denied["Retry-After"], "60")
        self.assertNotIn("198.51.100.1", str(middleware.buckets))


class PublicationTests(TestCase):
    def setUp(self):
        session = self.client.session
        session["sb_auth"] = ["holder", "test-password"]
        session.save()
        self.doc = {"id": "doc", "status": "ACTIVE", "claims": [], "claimCount": 1}
        self.result = {"id": bundle()["presentation"]["grantId"], "shareUrl": "http://localhost:8000" + PATH,
                       "disclosedCount": 1, "privateCount": 5, "expiresAt": "2026-10-15T00:00:00Z"}
        self.fields = {"claims": ["claim"], "expires_minutes": "30", "verifier_label": "Desk", "purpose": "Eligibility"}

    @patch("dashboard.wallet_views.tunnel_manager.confirm_public")
    @patch("dashboard.wallet_views.tunnel_manager.ensure_public", return_value=SNAPSHOT)
    @patch("dashboard.wallet_views.api.call")
    def test_public_url_preview_copy_and_qr_share_one_value(self, api, ensure, confirm):
        api.side_effect = [self.doc, self.result]
        response = self.client.post("/wallet/doc/share/", self.fields)
        self.assertContains(response, 'id="share-url" value="' + ORIGIN + PATH + '"')
        self.assertContains(response, 'href="' + ORIGIN + PATH + '"')
        self.assertContains(response, "Temporary public HTTPS link")
        self.assertNotContains(response, "http://localhost:8000")
        ensure.assert_called_once()
        confirm.assert_called_once_with(SNAPSHOT)

    @patch("dashboard.wallet_views.tunnel_manager.ensure_public", side_effect=tunnel.TunnelError("Tunnel unavailable"))
    @patch("dashboard.wallet_views.api.call")
    def test_startup_failure_precedes_grant_creation(self, api, ensure):
        api.return_value = self.doc
        response = self.client.post("/wallet/doc/share/", self.fields)
        self.assertContains(response, "Tunnel unavailable")
        api.assert_called_once_with("GET", "/api/wallet/documents/doc", ["holder", "test-password"])

    @patch("dashboard.wallet_views.tunnel_manager.confirm_public", side_effect=tunnel.TunnelError("Tunnel died"))
    @patch("dashboard.wallet_views.tunnel_manager.ensure_public", return_value=SNAPSHOT)
    @patch("dashboard.wallet_views.api.call")
    def test_failure_after_creation_revokes_unpublished_grant(self, api, ensure, confirm):
        api.side_effect = [self.doc, self.result, {}]
        response = self.client.post("/wallet/doc/share/", self.fields)
        self.assertContains(response, "The new grant was revoked")
        self.assertNotContains(response, TOKEN)
        self.assertEqual(api.call_args.args[1], "/api/wallet/disclosures/" + self.result["id"] + "/revoke")

    @patch("dashboard.wallet_views.tunnel_manager.confirm_public", side_effect=tunnel.TunnelError("Tunnel died"))
    @patch("dashboard.wallet_views.tunnel_manager.ensure_public", return_value=SNAPSHOT)
    @patch("dashboard.wallet_views.api.call")
    def test_failed_remedy_reports_active_grant_without_token(self, api, ensure, confirm):
        from .wallet_api import WalletAPIError
        api.side_effect = [self.doc, self.result, WalletAPIError("Unavailable")]
        response = self.client.post("/wallet/doc/share/", self.fields)
        self.assertContains(response, "may still be active; revoke it on the Shared page")
        self.assertNotContains(response, TOKEN)

    @patch.dict(os.environ, {"FOLIOLET_SHARE_MODE": "local"})
    @patch("dashboard.wallet_views.api.call")
    def test_explicit_local_mode_never_starts_tunnel(self, api):
        api.side_effect = [self.doc, self.result]
        with patch("dashboard.tunnel_manager.rpc") as rpc:
            response = self.client.post("/wallet/doc/share/", self.fields)
        self.assertContains(response, "Local-only link")
        self.assertContains(response, "http://localhost:8000" + PATH)
        rpc.assert_not_called()

    @patch("dashboard.wallet_views.tunnel_manager.ensure_public", return_value=SNAPSHOT)
    @patch("dashboard.wallet_views.api.call")
    def test_malformed_link_after_creation_is_revoked(self, api, ensure):
        api.side_effect = [self.doc, self.result | {"shareUrl": "http://[invalid"}, {}]
        response = self.client.post("/wallet/doc/share/", self.fields)
        self.assertContains(response, "The new grant was revoked")
        self.assertNotContains(response, TOKEN)

    @patch("dashboard.wallet_views.tunnel_manager.ensure_public", return_value=SNAPSHOT)
    @patch("dashboard.wallet_views.api.call")
    def test_ambiguous_create_timeout_reports_remedy_without_dead_link(self, api, ensure):
        from .wallet_api import WalletAPIError
        api.side_effect = [self.doc, WalletAPIError("Timeout", 503)]
        response = self.client.post("/wallet/doc/share/", self.fields)
        self.assertContains(response, "Check Shared for a new grant and revoke it before retrying")
        self.assertNotContains(response, 'id="share-url"')


class TunnelTests(SimpleTestCase):
    def test_control_key_initializes_fresh_clone_directory_and_is_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "fresh" / "receiver"
            with patch.object(tunnel, "STATE_DIR", state):
                key = tunnel.control_key()
                self.assertRegex(key, r"^[0-9a-f]{64}$")
                self.assertEqual(tunnel.control_key(), key)
                self.assertEqual((state / "control.key").read_text(), key)

    @patch.dict(os.environ, {"WALLET_SHARE_BASE_URL": "http://localhost:8008"})
    def test_isolated_desktop_share_origin_is_validated(self):
        self.assertEqual(tunnel.share_path("http://localhost:8008" + PATH), PATH)
        with self.assertRaises(tunnel.TunnelError):
            tunnel.share_path("http://localhost:8009" + PATH)

    def test_origin_and_token_validation(self):
        self.assertEqual(tunnel.validate_origin(ORIGIN), ORIGIN)
        self.assertEqual(tunnel.validate_origin("https://proofs.example.com", quick=False), "https://proofs.example.com")
        for origin in ("http://unit-receiver.trycloudflare.com", ORIGIN+"/", ORIGIN+"?x=1", ORIGIN+"#x",
                       "https://user@unit-receiver.trycloudflare.com", ORIGIN+":443", "https://trycloudflare.com",
                       "https://evil.trycloudflare.com.attacker.example", "https://127.0.0.1", "https://a.local"):
            with self.subTest(origin=origin), self.assertRaises(tunnel.TunnelError):
                tunnel.validate_origin(origin)
        for value in ("http://evil.example"+PATH, "http://localhost:8000/verify/short/",
                      "http://localhost:8000"+PATH+"?x=1", "http://localhost:8000"+PATH+"#x",
                      "http://user@localhost:8000"+PATH, "http://localhost:8000/verify/"+"A"*64+"/", "http://[invalid", None):
            with self.subTest(value=value), self.assertRaises(tunnel.TunnelError):
                tunnel.share_path(value)

    def supervisor(self):
        return tunnel.Supervisor({"mode": "quick", "port": 8001, "control": 8002, "timeout": 10})

    def test_simultaneous_ensures_start_one_child(self):
        owner = self.supervisor()
        def start():
            owner.origin = ORIGIN
            owner.child = Mock()
            owner.child.poll.return_value = None
        with (patch.object(owner, "start_origin"), patch.object(owner, "start_tunnel", side_effect=start) as spawned,
              patch.object(owner, "healthy", return_value=True)):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: owner.ensure(), range(2)))
        self.assertEqual(spawned.call_count, 1)
        self.assertEqual({r["origin"] for r in results}, {ORIGIN})

    def test_live_child_outage_fails_without_rotating_host(self):
        owner = self.supervisor()
        owner.state, owner.origin = "ready", ORIGIN
        owner.child = Mock()
        owner.child.poll.return_value = None
        with patch.object(owner, "healthy", return_value=False), patch.object(owner, "start_tunnel") as spawned:
            with self.assertRaises(tunnel.TunnelError):
                owner.ensure()
        spawned.assert_not_called()
        self.assertEqual(owner.origin, ORIGIN)

    def test_dead_child_status_and_recovery(self):
        owner = self.supervisor()
        owner.state, owner.origin = "ready", ORIGIN
        owner.child = Mock()
        owner.child.poll.return_value = 1
        self.assertEqual(owner.status()["state"], "unavailable")
        self.assertFalse(owner.status()["origin"])
        new_origin = "https://new-receiver.trycloudflare.com"
        def start():
            owner.origin = new_origin
            owner.child = Mock()
            owner.child.poll.return_value = None
        with (patch.object(owner, "start_origin"), patch.object(owner, "start_tunnel", side_effect=start),
              patch.object(owner, "healthy", side_effect=[False, True])):
            self.assertEqual(owner.ensure()["origin"], new_origin)

    def test_failed_start_and_stale_publication_fail_closed(self):
        owner = self.supervisor()
        with patch.object(owner, "start_origin"), patch.object(owner, "start_tunnel", side_effect=tunnel.TunnelError("Missing executable")):
            with self.assertRaises(tunnel.TunnelError):
                owner.ensure()
        self.assertEqual(owner.status()["state"], "unavailable")
        self.assertFalse(owner.status()["origin"])
        with patch.object(tunnel, "rpc", return_value=SNAPSHOT | {"origin": "https://new.trycloudflare.com"}):
            with self.assertRaises(tunnel.TunnelError):
                tunnel.confirm_public(SNAPSHOT)

    def test_startup_timeout_terminates_owned_connector_without_public_origin(self):
        owner = self.supervisor()
        child = Mock()
        child.poll.return_value = None
        def start():
            owner.child = child
            owner.origin = ORIGIN
        with (patch.object(owner, "start_origin"), patch.object(owner, "start_tunnel", side_effect=start),
              patch.object(tunnel.time, "monotonic", side_effect=[100, 111])):
            with self.assertRaisesRegex(tunnel.TunnelError, "readiness timed out"):
                owner.ensure()
        child.terminate.assert_called_once()
        child.wait.assert_called_once_with(timeout=5)
        self.assertEqual(owner.status()["state"], "unavailable")
        self.assertFalse(owner.status()["origin"])
        self.assertIsNone(owner.child)

    def test_other_receiver_instance_is_never_accepted_as_healthy(self):
        owner = self.supervisor()
        owner.origin = ORIGIN
        response = Mock(status_code=200)
        response.json.return_value = {"service": "foliolet-receiver", "instance": "another-checkout"}
        with patch.object(tunnel.requests, "get", return_value=response):
            self.assertFalse(owner.healthy())
        response.json.return_value = {"service": "foliolet-receiver", "instance": owner.instance}
        with patch.object(tunnel.requests, "get", return_value=response):
            self.assertTrue(owner.healthy())

    def test_actual_interprocess_lock_excludes_second_owner(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as directory, patch.object(tunnel, "STATE_DIR", Path(directory)):
            script = ("from pathlib import Path; import sys; from dashboard import tunnel_manager as t; "
                      "t.STATE_DIR=Path(sys.argv[1]);\nwith t.file_lock('owner',0): pass")
            with tunnel.file_lock("owner", 0):
                result = subprocess.run([sys.executable, "-c", script, directory], cwd=tunnel.ROOT / "django-service",
                                        capture_output=True, text=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Another share startup is busy", result.stderr)
            with tunnel.file_lock("owner", 0):
                pass

    def test_private_development_logs_suppress_bearers_and_queries(self):
        import logging
        from .wallet_security import ReceiverRequestLogFilter
        filter_ = ReceiverRequestLogFilter()
        for message in ("GET " + PATH, "GET /proof-download/uuid/", "GET /proof-status/uuid/", "GET /?token=hidden"):
            self.assertFalse(filter_.filter(logging.makeLogRecord({"msg": message})))
        self.assertTrue(filter_.filter(logging.makeLogRecord({"msg": "POST /wallet/document/share/"})))
