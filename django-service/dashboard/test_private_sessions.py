import io
import os
from pathlib import Path
import tempfile
from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core import signing
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from dashboard.private_sessions import EncryptedJSONSerializer, PREFIX, MAX_BYTES
from hermes.private_state import load_secret

SERIALIZER = 'dashboard.private_sessions.EncryptedJSONSerializer'


@override_settings(SECRET_KEY='fictional-test-key-'+'a'*48, SECRET_KEY_FALLBACKS=[], SESSION_SERIALIZER=SERIALIZER)
class PrivateSerializerTests(SimpleTestCase):
    def test_roundtrip_and_fresh_nonce(self):
        serializer = EncryptedJSONSerializer()
        value = {'sb_auth': ['fictional-holder', 'private-test-password'], 'unicode': 'தமிழ்'}
        first, second = serializer.dumps(value), serializer.dumps(value)
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith(PREFIX))
        self.assertNotIn(b'private-test-password', first)
        self.assertEqual(serializer.loads(first), value)

    def test_tampering_and_other_receiver_key_fail_closed(self):
        serializer = EncryptedJSONSerializer(); raw = serializer.dumps({'secret': 'fictional'})
        changed = raw[:-1] + bytes([raw[-1] ^ 1])
        with self.assertRaises(ValueError): serializer.loads(changed)
        with override_settings(SECRET_KEY='separate-receiver-key-'+'b'*48):
            with self.assertRaises(ValueError): serializer.loads(raw)

    def test_explicit_key_fallback_preserves_old_sessions(self):
        serializer = EncryptedJSONSerializer(); raw = serializer.dumps({'retained': True})
        previous = settings.SECRET_KEY
        with override_settings(SECRET_KEY='new-explicit-key-'+'c'*48, SECRET_KEY_FALLBACKS=[previous]):
            self.assertEqual(serializer.loads(raw), {'retained': True})

    def test_legacy_is_json_only_and_limits_are_enforced(self):
        serializer = EncryptedJSONSerializer()
        self.assertEqual(serializer.loads(b'{"legacy":true}'), {'legacy': True})
        for raw in (b'not-json', PREFIX+b'short', b'x'*(MAX_BYTES+100)):
            with self.assertRaises(ValueError): serializer.loads(raw)
        with self.assertRaises(ValueError): serializer.dumps({'too-large': 'x'*(MAX_BYTES+1)})


@override_settings(SECRET_KEY='fictional-test-key-'+'a'*48, SECRET_KEY_FALLBACKS=[], SESSION_SERIALIZER=SERIALIZER)
class PrivateSessionDatabaseTests(TestCase):
    def test_actual_database_store_remains_readable_without_exposing_plaintext(self):
        store = SessionStore(); store['sb_auth'] = ['fictional-holder', 'unique-private-password']; store.create()
        row = Session.objects.get(session_key=store.session_key)
        class Raw:
            def loads(self, data): return data
        raw = signing.loads(row.session_data, salt=store.key_salt, serializer=Raw)
        self.assertTrue(raw.startswith(PREFIX))
        self.assertNotIn(b'unique-private-password', raw)
        self.assertEqual(SessionStore(session_key=store.session_key)['sb_auth'], ['fictional-holder', 'unique-private-password'])
        self.assertEqual(row.get_decoded()['sb_auth'], ['fictional-holder', 'unique-private-password'])

    def test_migration_preserves_identity_expiry_and_legacy_credentials(self):
        store = SessionStore(); store['sb_auth'] = ['old-holder', 'old-password']; store.create()
        row = Session.objects.get(session_key=store.session_key)
        legacy = signing.dumps({'sb_auth': ['old-holder', 'old-password']}, salt=store.key_salt, serializer=signing.JSONSerializer, compress=True)
        row.session_data = legacy; row.save(update_fields=['session_data']); expiry = row.expire_date
        self.assertEqual(SessionStore(session_key=row.session_key)['sb_auth'], ['old-holder', 'old-password'])
        call_command('reencrypt_sessions', dry_run=True, stdout=io.StringIO())
        row.refresh_from_db(); self.assertEqual(row.session_data, legacy)
        call_command('reencrypt_sessions', stdout=io.StringIO())
        row.refresh_from_db(); self.assertNotEqual(row.session_data, legacy)
        self.assertEqual(row.expire_date, expiry)
        self.assertEqual(row.get_decoded()['sb_auth'], ['old-holder', 'old-password'])
        encrypted = row.session_data
        call_command('reencrypt_sessions', stdout=io.StringIO())
        row.refresh_from_db(); self.assertEqual(row.session_data, encrypted)


class PrivateStateTests(SimpleTestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(); self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name)/'state'/'django.key'

    def test_created_key_is_preserved_on_restart_and_existing_permissions_harden(self):
        first = load_secret(self.path); expected = self.path.read_bytes()
        self.assertEqual(load_secret(self.path), first)
        self.assertEqual(self.path.read_bytes(), expected)
        if os.name == 'posix':
            self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(self.path.parent.stat().st_mode & 0o777, 0o700)

    def test_invalid_existing_key_is_never_replaced(self):
        self.path.parent.mkdir(); self.path.write_bytes(b'invalid')
        with self.assertRaises(ValueError): load_secret(self.path)
        self.assertEqual(self.path.read_bytes(), b'invalid')

    def test_symlink_key_is_refused_without_changing_target(self):
        if os.name == 'nt': self.skipTest('Symlink privilege is not assumed on Windows')
        self.path.parent.mkdir(); outside = self.path.parent.parent/'outside.key'; outside.write_bytes(b'x'*64)
        self.path.symlink_to(outside)
        with self.assertRaises(OSError): load_secret(self.path)
        self.assertEqual(outside.read_bytes(), b'x'*64)

    def test_explicit_environment_key_is_not_persisted(self):
        self.assertEqual(load_secret(self.path, 'explicit-test-key'), 'explicit-test-key')
        self.assertFalse(self.path.exists())
