"""The Docker companion still requires private, authenticated, explicit consent."""
import json
import os
from pathlib import Path
import tempfile
import uuid
from unittest.mock import patch
from django.test import TestCase, override_settings
from .test_scan import AUTH
from .managed_watcher import enqueue

@override_settings(FOLIOLET_MANAGED_WATCHER=True, SPRING_BOOT_API_BASE_URL='http://127.0.0.1:8088',
                   FOLIOLET_HOST_INTAKE_FOLDER='/Users/holder/Downloads/Foliolet Intake')
class ManagedWatcherTests(TestCase):
    def setUp(self):
        session = self.client.session
        session['sb_auth'], session['sb_username'] = AUTH, 'holder'
        session.save()
        self.config = {'sessionId': str(uuid.uuid4()), 'token': 'synthetic-secret',
                       'folder': '/host/intake/documents-inbox'}

    @patch('dashboard.intake_views.api.call')
    @patch('dashboard.managed_watcher.enqueue')
    def test_browser_never_receives_pairing_secret_or_controls_mounted_folder(self, queue, api):
        api.return_value = self.config.copy()
        response = self.client.post('/intake/pair/', {'folder': '/etc', 'consent': 'yes'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'managed': True, 'sessionId': self.config['sessionId']})
        self.assertNotIn('Content-Disposition', response)
        self.assertNotContains(response, 'synthetic-secret')
        api.assert_called_once_with('POST', '/api/wallet/intake/sessions', AUTH,
                                    payload={'folder': '/host/intake/documents-inbox'})
        self.assertEqual(queue.call_args.args[0]['apiUrl'], 'http://127.0.0.1:8088')

    @patch('dashboard.intake_views.api.call')
    @patch('dashboard.managed_watcher.enqueue')
    def test_no_consent_no_session_or_companion(self, queue, api):
        self.assertEqual(self.client.post('/intake/pair/', {'folder': '/etc'}).status_code, 400)
        api.assert_not_called(); queue.assert_not_called()

    @patch('dashboard.intake_views.api.call')
    @patch('dashboard.managed_watcher.enqueue', side_effect=OSError('private filesystem detail'))
    def test_failed_private_delivery_revokes_session_and_has_manual_fallback(self, queue, api):
        api.return_value = self.config.copy()
        response = self.client.post('/intake/pair/', {'consent': 'yes'})
        self.assertEqual(response.status_code, 503)
        self.assertNotContains(response, 'private filesystem detail', status_code=503)
        self.assertEqual(api.call_args.args[1], f"/api/wallet/intake/sessions/{self.config['sessionId']}/stop")

    @patch('dashboard.wallet_views.api.call', return_value=[])
    def test_docker_screen_shows_host_folder_without_json_or_terminal_steps(self, api):
        response = self.client.get('/wallet/enroll/')
        self.assertContains(response, 'data-managed="yes"')
        self.assertContains(response, '/Users/holder/Downloads/Foliolet Intake')
        self.assertContains(response, 'readonly')
        self.assertNotContains(response, 'start-digilocker-watcher.ps1')
        self.assertNotContains(response, '/host/intake')

    @patch('dashboard.intake_views.api.call')
    def test_connection_screen_displays_the_host_folder(self, api):
        api.return_value = [{'folder': '/host/intake/documents-inbox'}]
        self.assertEqual(self.client.get('/intake/sessions/').json()['sessions'][0]['folder'],
                         '/Users/holder/Downloads/Foliolet Intake')

    def test_pairing_is_atomic_private_and_path_confined(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(FOLIOLET_PAIRING_DIR=directory):
            enqueue(self.config)
            file = Path(directory) / (self.config['sessionId']+'.json')
            self.assertEqual(json.loads(file.read_text())['token'], 'synthetic-secret')
            self.assertEqual(len(list(Path(directory).iterdir())), 1)
            if os.name != 'nt': self.assertEqual(file.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError): enqueue(dict(self.config, sessionId='../../escape'))
            with self.assertRaises(ValueError): enqueue(dict(self.config, token='x'*17000))
