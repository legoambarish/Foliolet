"""Exact current-folder selection, owner isolation and live inventory regressions."""
import os
from pathlib import Path
import tempfile
from unittest.mock import patch
from django.core import signing
from django.test import Client, TestCase, override_settings
from . import tracked_files
from .test_receiver import PROFILE, HOST


@override_settings(SPRING_BOOT_API_BASE_URL='http://127.0.0.1:8088')
class TrackedFileTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / 'incoming'
        self.folder.mkdir()
        self.active = {'id': '00000000-0000-4000-8000-000000000001', 'folder': str(self.folder), 'active': True, 'connected': True}
        self.auth = ['current-holder', 'synthetic-password']
        session = self.client.session
        session['sb_auth'] = self.auth
        session.save()

    def write(self, name, content=b'Synthetic document', mtime=None):
        path = self.folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        if mtime: os.utime(path, (mtime, mtime))
        return path

    @patch('dashboard.intake_views.api.call')
    def test_all_current_folder_files_are_sorted_and_refreshed_without_old_receipts(self, api):
        self.write('old.txt', mtime=1700000000)
        self.write('nested/new.csv', mtime=1700000010)
        self.write('partial.pdf.crdownload')
        self.write('.hidden.txt')
        self.write('unsupported.docx')
        self.write('empty.txt', b'')
        historical = {**self.active, 'id': 'old-session', 'active': False, 'documents': [{'id': 'old-document'}]}
        api.return_value = [self.active, historical]
        response = self.client.get('/intake/files/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'no-store, private')
        self.assertEqual([row['relativePath'] for row in response.json()['files']], ['nested/new.csv', 'old.txt'])
        self.write('newest.txt', mtime=1700000020)
        self.assertEqual(self.client.get('/intake/files/').json()['files'][0]['name'], 'newest.txt')
        (self.folder / 'newest.txt').unlink()
        self.assertEqual(len(self.client.get('/intake/files/').json()['files']), 2)
        api.return_value = [historical]
        self.assertEqual(self.client.get('/intake/files/').json()['files'], [])

    @patch('dashboard.intake_views.api.call')
    def test_selected_row_sends_its_exact_bytes_and_rejects_replaced_file(self, api):
        self.write('first.txt', b'first document')
        path = self.write('second.txt', b'exact second document')
        rows = tracked_files.inventory(self.active, self.auth[0])
        token = next(row['selection'] for row in rows if row['name'] == 'second.txt')
        credential = '0x' + '12' * 32
        api.side_effect = [[self.active], {'id': credential}]
        response = self.client.post('/intake/files/import/', {'selection': token})
        self.assertEqual(response.json()['url'], f'/wallet/{credential}/')
        self.assertEqual(api.call_args.kwargs['files']['file'][0:2], ('second.txt', b'exact second document'))
        self.assertEqual(api.call_args.kwargs['data']['relativePath'], 'second.txt')
        path.write_bytes(b'changed bytes')
        api.reset_mock(); api.side_effect = None; api.return_value = [self.active]
        self.assertEqual(self.client.post('/intake/files/import/', {'selection': token}).status_code, 409)
        self.assertEqual(api.call_count, 1)

    @patch('dashboard.intake_views.api.call')
    def test_pairing_holder_tampering_revocation_and_deleted_files_fail_closed(self, api):
        path = self.write('document.txt')
        token = tracked_files.inventory(self.active, self.auth[0])[0]['selection']
        api.return_value = [{**self.active, 'id': 'replacement-session'}]
        self.assertEqual(self.client.post('/intake/files/import/', {'selection': token}).status_code, 409)
        api.return_value = [self.active]
        foreign = tracked_files.inventory(self.active, 'another-holder')[0]['selection']
        for value in (foreign, token + 'tampered'):
            self.assertEqual(self.client.post('/intake/files/import/', {'selection': value}).status_code, 409)
        path.unlink()
        self.assertEqual(self.client.post('/intake/files/import/', {'selection': token}).status_code, 409)
        api.return_value = []
        self.assertEqual(self.client.post('/intake/files/import/', {'selection': token}).status_code, 409)

    @patch('dashboard.intake_views.api.call')
    def test_login_loopback_csrf_and_methods_are_required(self, api):
        self.assertEqual(Client().get('/intake/files/').status_code, 401)
        self.assertEqual(self.client.get('/intake/files/', REMOTE_ADDR='192.0.2.1').status_code, 404)
        self.assertEqual(self.client.get('/intake/files/import/').status_code, 405)
        client = Client(enforce_csrf_checks=True)
        session = client.session; session['sb_auth'] = self.auth; session.save()
        self.assertEqual(client.post('/intake/files/import/', {'selection': 'anything'}).status_code, 403)
        api.assert_not_called()

    def test_external_path_and_incomplete_pdf_are_refused(self):
        self.write('unfinished.pdf', b'%PDF-1.7\nnot finished')
        token = tracked_files.inventory(self.active, self.auth[0])[0]['selection']
        with self.assertRaises(OSError): tracked_files.read_selection(token, self.active, self.auth[0])
        selected = signing.loads(token, salt=tracked_files.SALT)
        selected['relative'] = '../outside.txt'
        bad = signing.dumps(selected, salt=tracked_files.SALT)
        with self.assertRaises((ValueError, OSError)): tracked_files.read_selection(bad, self.active, self.auth[0])

    @override_settings(**PROFILE)
    @patch('dashboard.intake_views.api.call')
    def test_receiver_never_exposes_inventory_or_import(self, api):
        for route in ('/intake/files/', '/intake/files/import/'):
            for method in ('get', 'post'):
                self.assertEqual(getattr(self.client, method)(route, secure=True, HTTP_HOST=HOST).status_code, 404)
        api.assert_not_called()
