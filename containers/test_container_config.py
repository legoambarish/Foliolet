"""Adversarial private-control validation. No network, models or user data needed."""
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import uuid

spec = importlib.util.spec_from_file_location('managed_companion', Path(__file__).with_name('watcher.py'))
watcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watcher)

class PairingBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.name = str(uuid.uuid4())
        self.file = Path(self.temporary.name) / (self.name + '.json')
        self.data = {'sessionId': self.name, 'folder': watcher.FOLDER,
                     'folderHash': hashlib.sha256(watcher.FOLDER.encode()).hexdigest(),
                     'apiUrl': 'http://127.0.0.1:8088',
                     'expiresAt': (datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat()}
    def validate(self, **changes):
        self.file.write_text(json.dumps(dict(self.data, **changes)))
        return watcher.validate(self.file)
    def test_accepts_only_bounded_real_pairing_shape(self):
        self.assertEqual(self.validate(), self.name)
    def test_rejects_remote_hostname_url_credentials_and_broad_folder(self):
        for url in ('https://example.com', 'http://backend:8088', 'http://127.0.0.1:8088@evil.example', 'http://localhost:8088'):
            with self.assertRaises(ValueError): self.validate(apiUrl=url)
        for folder in ('/etc', '/Users', '/host/intake/documents-inbox/../..'):
            with self.assertRaises(ValueError): self.validate(folder=folder)
    def test_session_filename_cannot_be_retargeted(self):
        with self.assertRaises(ValueError): self.validate(sessionId=str(uuid.uuid4()))
        with self.assertRaises(ValueError): self.validate(sessionId='../../escape')
    def test_modified_folder_hash_is_rejected(self):
        with self.assertRaises(ValueError): self.validate(folderHash='0'*64)
    def test_expired_and_unbounded_capabilities_are_rejected(self):
        for delta in (-1, 3600):
            expiry=(datetime.now(timezone.utc)+timedelta(seconds=delta)).isoformat()
            with self.assertRaises(ValueError): self.validate(expiresAt=expiry)
    def test_oversized_and_malformed_pairings_are_rejected(self):
        self.file.write_text('x'*16385)
        with self.assertRaises(ValueError): watcher.validate(self.file)
        self.file.write_text('{"untrusted":true}')
        with self.assertRaises(KeyError): watcher.validate(self.file)
    def test_symlink_cannot_import_control_file(self):
        target=Path(self.temporary.name)/'elsewhere'
        target.write_text(json.dumps(self.data))
        try: self.file.symlink_to(target)
        except OSError: self.skipTest('OS does not allow this account to create symlinks')
        with self.assertRaises(ValueError): watcher.validate(self.file)

if __name__ == '__main__': unittest.main(verbosity=2)
