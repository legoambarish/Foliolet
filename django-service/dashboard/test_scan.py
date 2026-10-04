"""Scan-for-fields boundary tests. The Spring bridge is mocked here; the model call lives in Spring."""
from unittest.mock import patch
from django.test import TestCase, Client
from .wallet_api import WalletAPIError

AUTH = ["holder", "a-long-password"]


def draft(status="DRAFT"):
    return {"id": "abc", "displayName": "Lease", "category": "Other", "version": 1, "status": status,
            "provenanceLevel": "SELF_ENROLLED", "provenance": {}, "claims": [], "suggestions": [],
            "merkleRoot": None}


class ScanFieldsTests(TestCase):
    def sign_in(self, client=None):
        client = client or self.client
        session = client.session
        session["sb_auth"] = AUTH
        session["sb_username"] = "holder"
        session.save()
        return client

    def test_requires_login(self):
        with patch("dashboard.wallet_views.api.call") as api:
            response = self.client.post("/wallet/abc/scan/")
        self.assertRedirects(response, "/login/", fetch_redirect_response=False)
        api.assert_not_called()

    def test_post_only(self):
        self.sign_in()
        with patch("dashboard.wallet_views.api.call") as api:
            self.assertEqual(self.client.get("/wallet/abc/scan/").status_code, 405)
        api.assert_not_called()

    def test_csrf_required(self):
        client = self.sign_in(Client(enforce_csrf_checks=True))
        with patch("dashboard.wallet_views.api.call") as api:
            self.assertEqual(client.post("/wallet/abc/scan/").status_code, 403)
        api.assert_not_called()

    def test_returns_only_well_formed_suggestions(self):
        self.sign_in()
        good = {"path": "person.name", "label": "Full name", "type": "string", "value": "Rohan", "evidence": "Name: Rohan"}
        spring = {"fields": [good, {"path": "x"}, "junk", {**good, "type": "object"}, {**good, "value": 5}],
                  "discarded": 2, "source": "text", "internal": "never forwarded"}
        with patch("dashboard.wallet_views.api.call", return_value=spring) as api:
            response = self.client.post("/wallet/abc/scan/")
        api.assert_called_once_with("POST", "/api/wallet/documents/abc/scan", AUTH)
        self.assertEqual(response.json(), {"fields": [good], "discarded": 2, "source": "text"})
        self.assertEqual(response["Cache-Control"], "no-store, private")

    def test_garbage_from_the_service_yields_an_empty_list(self):
        self.sign_in()
        with patch("dashboard.wallet_views.api.call", return_value="<html>oops</html>"):
            body = self.client.post("/wallet/abc/scan/").json()
        self.assertEqual(body, {"fields": [], "discarded": 0, "source": "text"})

    def test_service_errors_are_reported_not_hidden(self):
        self.sign_in()
        error = WalletAPIError("Field scanning is not configured.", 503)
        with patch("dashboard.wallet_views.api.call", side_effect=error):
            response = self.client.post("/wallet/abc/scan/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"error": "Field scanning is not configured."})
        with patch("dashboard.wallet_views.api.call", side_effect=WalletAPIError("odd", 99)):
            self.assertEqual(self.client.post("/wallet/abc/scan/").status_code, 502)


class ScanButtonTests(TestCase):
    def page(self, status):
        session = self.client.session
        session["sb_auth"] = AUTH
        session["sb_username"] = "holder"
        session.save()
        with patch("dashboard.wallet_views.api.call", return_value=draft(status)):
            return self.client.get("/wallet/abc/")

    def test_draft_review_offers_the_scan(self):
        response = self.page("DRAFT")
        self.assertContains(response, 'id="scan-fields"')
        self.assertContains(response, 'data-url="/wallet/abc/scan/"')
        self.assertContains(response, "Nothing is saved until you confirm")

    def test_anchored_document_has_no_scan(self):
        self.assertNotContains(self.page("ACTIVE"), 'id="scan-fields"')
