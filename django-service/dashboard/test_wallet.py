"""UI boundaries; bridge mocked here only. Actual backend/chain exercised by tools/test-live-workflow.py."""
from unittest.mock import patch
from django.test import TestCase, Client
from .wallet_api import WalletAPIError
from . import proof_cache
from .test_security import bundle as valid_bundle, passed


class WalletSurfaceTests(TestCase):
    def test_private_page_requires_login(self):
        self.assertRedirects(self.client.get("/"), "/login/", fetch_redirect_response=False)

    @patch("dashboard.wallet_views.api.call")
    def test_get_does_not_consume_or_release_bearer_link(self, api):
        response = self.client.get("/verify/" + "a"*64 + "/")
        self.assertEqual(response.status_code, 200)
        api.assert_not_called()
        self.assertContains(response, "Open disclosed facts")
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["Referrer-Policy"], "strict-origin")

    @patch("dashboard.wallet_views.api.call")
    def test_csrf_required_for_release(self, api):
        response = Client(enforce_csrf_checks=True).post("/verify/" + "a"*64 + "/")
        self.assertEqual(response.status_code, 403)
        api.assert_not_called()

    @patch("dashboard.wallet_views.api.call", side_effect=WalletAPIError("Chain unavailable", 503))
    def test_unavailable_chain_cannot_display_pass(self, api):
        response = self.client.post("/verify/" + "a"*64 + "/")
        self.assertContains(response, "No facts have been shown")
        self.assertNotContains(response, "Service verification passed")
        self.assertEqual(api.call_count, 1)

    def test_legacy_legal_surface_is_opt_in(self):
        self.assertEqual(self.client.get("/legacy/").status_code, 404)

    def test_invalid_bearer_shape_is_rejected(self):
        self.assertEqual(self.client.get("/verify/short/").status_code, 404)

    @patch("dashboard.wallet_views.api.call")
    def test_bundle_export_requires_previously_released_session(self, api):
        self.assertEqual(self.client.get("/proof-download/random/").status_code, 404)
        api.assert_not_called()

    @patch("dashboard.wallet_views.api.call", return_value=passed())
    def test_export_does_not_reconsume_one_time_grant(self, api):
        bundle = valid_bundle()
        grant_id = bundle['presentation']['grantId']
        session = self.client.session
        session["released_proofs"] = {grant_id: proof_cache.seal(bundle)}
        session.save()
        response = self.client.get(f"/proof-download/{grant_id}/")
        self.assertEqual(response.json(), bundle)
        self.assertIn("attachment", response["Content-Disposition"])
        api.assert_called_once_with("POST", "/api/public/verify-bundle", payload=bundle)

    @patch("dashboard.wallet_views.api.call", return_value={"verified": False})
    def test_revoked_or_expired_export_fails_closed(self, api):
        bundle = valid_bundle()
        grant_id = bundle['presentation']['grantId']
        session = self.client.session
        session["released_proofs"] = {grant_id: proof_cache.seal(bundle)}
        session.save()
        response = self.client.get(f"/proof-download/{grant_id}/")
        self.assertEqual(response.status_code, 410)
        self.assertNotContains(response, '"private"', status_code=410)

    def test_export_cache_authenticates_ciphertext_and_grant_context(self):
        bundle = {"presentation": {"grantId": "released"}, "claims": [{"value": "private"}]}
        sealed = proof_cache.seal(bundle)
        self.assertNotIn("private", sealed)
        self.assertEqual(proof_cache.open_proof("released", sealed), bundle)
        with self.assertRaises(ValueError):
            proof_cache.open_proof("different-grant", sealed)
