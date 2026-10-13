from django.test import SimpleTestCase, override_settings
from unittest.mock import patch
import json

@override_settings(ROOT_URLCONF='hermes.public_urls')
class PublicSurfaceTests(SimpleTestCase):
    def test_private_routes_absent(self):
        for route in ['/admin/', '/login/', '/register/', '/bridge/', '/bridge/api/plans/', '/wallet/anything/file/', '/bridge/upload/']:
            self.assertEqual(self.client.get(route).status_code, 404, route)

    def test_public_discovery_releases_no_facts(self):
        response = self.client.get('/discover/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'fresh request')
        self.assertContains(response, 'clonable')
        self.assertEqual(response['Cache-Control'], 'no-store, private')

    @patch('dashboard.bridge_views.api.call')
    def test_share_get_does_not_consume_opening(self, call):
        response = self.client.get('/share/0x' + 'a'*64 + '/')
        self.assertEqual(response.status_code, 200)
        call.assert_not_called()

    @patch('dashboard.bridge_views.api.call', return_value={'active': False, 'opens': 1, 'expiresAt': 10})
    def test_status_has_no_protected_fields(self, call):
        response = self.client.get('/share/0x' + 'a'*64 + '/status/')
        self.assertEqual(response.json(), {'active': False, 'opens': 1, 'expiresAt': 10})

    def test_callback_does_not_trust_success_flag(self):
        response = self.client.get('/imports/callback/?success=True&id=spoofed')
        self.assertContains(response, 'does not establish consent')
