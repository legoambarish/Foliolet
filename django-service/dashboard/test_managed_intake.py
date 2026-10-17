import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from django.test import TestCase, override_settings


class ManagedIntakeTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / 'incoming'; self.folder.mkdir()
        self.override = override_settings(MANAGED_INTAKE=True, INTAKE_FOLDER=str(self.folder),
            BASE_DIR=self.root / 'django-service', SPRING_BOOT_API_BASE_URL='http://127.0.0.1:8088')
        self.override.enable(); self.addCleanup(self.override.disable)
        session = self.client.session; session['sb_auth'] = ['holder-one', 'synthetic']; session.save()
        self.config = {'folder':str(self.folder), 'sessionId':'00000000-0000-4000-8000-000000000001',
            'folderHash':hashlib.sha256(str(self.folder).encode()).hexdigest(), 'token':'12'*32,
            'agentId':'synthetic-agent', 'secret':'34'*32, 'lifetime':'app', 'expiresAt':None}

    @patch('dashboard.intake_views.api.call')
    def test_pair_starts_managed_flow_without_downloading_a_capability(self, api):
        api.return_value = self.config
        response = self.client.post('/intake/pair/', {'folder':str(self.folder),'consent':'yes'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'managed':True,'sessionId':self.config['sessionId']})
        self.assertNotIn('Content-Disposition', response)
        slot = hashlib.sha256(b'holder-one').hexdigest()
        saved = self.root / '.local-data/managed-intake' / (slot + '.json')
        self.assertEqual(json.loads(saved.read_text())['token'], self.config['token'])
        self.assertNotIn(self.config['token'], response.content.decode())

    @patch('dashboard.intake_views.api.call')
    def test_only_the_mounted_folder_with_consent_can_be_paired(self, api):
        self.assertEqual(self.client.post('/intake/pair/', {'folder':str(self.root),'consent':'yes'}).status_code, 400)
        self.assertEqual(self.client.post('/intake/pair/', {'folder':str(self.folder)}).status_code, 400)
        api.assert_not_called()

    @patch('dashboard.wallet_views.api.call', return_value=[])
    def test_container_ui_uses_automatic_watcher_instructions(self, api):
        response = self.client.get('/wallet/enroll/')
        self.assertContains(response, 'data-managed="yes"')
        self.assertContains(response, 'watcher connects automatically')
        self.assertNotContains(response, 'start-digilocker-watcher.ps1')
