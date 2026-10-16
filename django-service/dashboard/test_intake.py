"""Private intake proxy, consent, CSRF and receiver isolation regressions."""
from unittest.mock import patch
from django.test import Client, TestCase, override_settings
from .test_receiver import PROFILE, HOST
from .test_scan import AUTH, draft
from .wallet_api import WalletAPIError


@override_settings(SPRING_BOOT_API_BASE_URL='http://127.0.0.1:8088')
class IntakeTests(TestCase):
    def login(self, client=None):
        client = client or self.client
        session = client.session
        session['sb_auth'] = AUTH
        session['sb_username'] = 'holder'
        session.save()
        return client

    @patch('dashboard.intake_views.api.call')
    def test_session_login_loopback_consent_and_method_are_required(self, api):
        self.assertEqual(self.client.get('/intake/sessions/').status_code, 401)
        self.login()
        self.assertEqual(self.client.post('/intake/pair/', {'folder': r'C:\Users\User\Downloads\Foliolet Intake'}).status_code, 400)
        self.assertEqual(self.client.get('/intake/pair/').status_code, 405)
        self.assertEqual(self.client.get('/intake/sessions/', REMOTE_ADDR='192.0.2.1').status_code, 404)
        api.assert_not_called()

    @patch('dashboard.intake_views.api.call')
    def test_csrf_protects_pair_stop_and_retry(self, api):
        client = self.login(Client(enforce_csrf_checks=True))
        for route in ('/intake/pair/', '/intake/sessions/00000000-0000-4000-8000-000000000000/stop/', '/intake/documents/synthetic/retry/'):
            self.assertEqual(client.post(route, {'folder': 'x', 'consent': 'yes'}).status_code, 403)
        api.assert_not_called()

    @patch('dashboard.intake_views.api.call', return_value={'sessionId': 'synthetic', 'token': 'test-secret'})
    def test_pair_is_a_private_machine_download_and_api_origin_is_fixed(self, api):
        self.login()
        response = self.client.post('/intake/pair/', {'folder': r'C:\Users\User\Downloads\Foliolet Intake', 'consent': 'yes', 'apiUrl': 'https://evil.example'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['apiUrl'], 'http://127.0.0.1:8088')
        self.assertEqual(response['Cache-Control'], 'no-store, private')
        self.assertIn('attachment', response['Content-Disposition'])
        api.assert_called_once_with('POST', '/api/wallet/intake/sessions', AUTH, payload={'folder': r'C:\Users\User\Downloads\Foliolet Intake'})

    @override_settings(SPRING_BOOT_API_BASE_URL='https://remote.example')
    @patch('dashboard.intake_views.api.call')
    def test_nonlocal_configuration_fails_before_creating_a_session(self, api):
        self.login()
        self.assertEqual(self.client.post('/intake/pair/', {'folder': 'x', 'consent': 'yes'}).status_code, 400)
        api.assert_not_called()

    @patch('dashboard.intake_views.api.call')
    def test_owner_errors_and_outages_remain_explicit(self, api):
        self.login()
        for status in (404, 409, 429, 503):
            api.side_effect = WalletAPIError('Synthetic failure', status)
            response = self.client.get('/intake/documents/synthetic/')
            self.assertEqual(response.status_code, status)
            self.assertEqual(response['Cache-Control'], 'no-store, private')

    @patch('dashboard.wallet_views.api.call', return_value=[])
    def test_official_link_manual_fallback_and_no_secret_or_affiliation_claim(self, api):
        self.login()
        response = self.client.get('/wallet/enroll/')
        self.assertContains(response, 'href="https://www.digilocker.gov.in/" target="_blank" rel="noopener noreferrer"')
        self.assertContains(response, 'name="file"')
        self.assertContains(response, 'not affiliated with DigiLocker')
        self.assertContains(response, 'Local watcher not connected')
        self.assertNotContains(response, 'test-secret')
        self.assertNotContains(response, '<iframe')

    @patch('dashboard.wallet_views.api.call')
    def test_review_has_source_quotes_separate_labels_and_hidden_advanced_paths(self, api):
        self.login()
        doc = draft()
        doc['intake'] = {'format': 'pdf', 'method': 'WATCHER_ASSISTED', 'state': 'READY', 'indicator': 'POSSIBLE_DIGILOCKER_FORMAT',
                         'lineage': 'SUGGESTIONS_MODIFIED', 'issuer': 'NOT_VERIFIED',
                         'changes': {'edited': 1, 'added': 0, 'removed': 0},
                         'fields': [{'path': 'education.math', 'label': 'Math', 'type': 'decimal', 'value': '90',
                                     'evidence': 'Math: 90', 'citation': {'page': 1, 'provenance': 'OCR transcription'}}]}
        api.return_value = doc
        response = self.client.get('/wallet/abc/')
        for text in ('Possible DigiLocker document (unverified)', 'Imported with Foliolet', 'Issuer not verified',
                     'Facts edited since extraction', 'Math: 90', '<summary>Advanced</summary>', 'Review the original AI proposal'):
            self.assertContains(response, text)
        self.assertContains(response, 'value="90"')
        self.assertNotContains(response, 'Verified DigiLocker')

    @patch('dashboard.wallet_views.api.call')
    def test_names_and_values_do_not_require_user_to_type_paths(self, api):
        self.login()
        api.return_value = draft()
        response = self.client.post('/wallet/abc/', {'claim_path': '', 'claim_label': 'Math', 'claim_type': 'decimal', 'claim_value': '90', 'confirm': 'yes'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(api.call_args.kwargs['payload']['claims'][0]['path'], 'education.math')


@override_settings(**PROFILE)
class IntakeReceiverTests(TestCase):
    @patch('dashboard.intake_views.api.call')
    def test_public_surface_has_no_intake_routes_or_assets(self, api):
        for route in ('/intake/pair/', '/intake/sessions/', '/intake/documents/synthetic/', '/intake/documents/synthetic/retry/',
                      '/api/intake-agent/upload', '/api/wallet/intake/sessions', '/static/wallet/intake.js'):
            for method in ('get', 'post'):
                response = getattr(self.client, method)(route, secure=True, HTTP_HOST=HOST)
                expected = 405 if route.startswith('/static/') and method == 'post' else 404
                self.assertEqual(response.status_code, expected, (route, method))
        api.assert_not_called()
