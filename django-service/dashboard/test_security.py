import importlib
import copy
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from . import proof_cache


def bundle():
    return {
        'format': 'salted-merkle-keccak-v1', 'credentialId': '0x' + '11'*32,
        'credentialVersion': 1, 'merkleRoot': '0x' + '22'*32, 'leafCount': 1,
        'anchor': {'contract': '0x'+'33'*20, 'operator': '0x'+'44'*20, 'chainId': 1337,
                   'documentCommitment': '0x'+'55'*32, 'provenanceDigest': '0x'+'66'*32,
                   'provenanceCode': 0, 'anchoredAt': '2026-10-02T00:00:00Z', 'txHash': None},
        'provenance': {'level': 'SELF_ENROLLED', 'explanation': 'Holder confirmed',
                       'observations': 0, 'observedChanges': False, 'enrollmentMatchesFirst': False,
                       'firstReceivedAt': None, 'lastReceivedAt': None, 'agentId': None},
        'presentation': {'grantId': '11111111-1111-4111-8111-111111111111', 'verifierLabel': 'Desk',
                         'purpose': 'Eligibility', 'nonce': '0x'+'77'*32, 'oneTime': True,
                         'createdAt': '2026-10-02T00:00:00Z', 'expiresAt': '2026-10-02T01:00:00Z'},
        'claims': [{'leaf': {'path': 'custom.eligibility', 'label': 'CGPA at least 8.5',
                            'type': 'boolean', 'value': 'true', 'derivedFrom': '',
                            'salt': '0x'+'88'*32, 'index': 0}, 'proof': []}],
        'envelopeHash': '0x'+'99'*32, 'platformSignature': '0x'+'aa'*65,
    }


def passed():
    return dict.fromkeys(('proofValid', 'signatureValid', 'anchorMatches', 'current',
                         'policyActive', 'verified'), True) | {'message': 'Verified'}


class SecurityRegressionTests(TestCase):
    def login_session(self):
        session = self.client.session
        session['sb_auth'] = ['holder', 'password']
        session.save()

    @patch('dashboard.wallet_views.api.call')
    def test_extracted_values_never_enter_session(self, api):
        self.login_session()
        api.side_effect = [[], {'id': 'doc', 'suggestions': [{'value': 'SECRET NAME'}]}]
        response = self.client.post('/wallet/enroll/', {'file': SimpleUploadedFile('marks.txt', b'Name: SECRET NAME')})
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('claim_suggestions', self.client.session)
        self.assertNotIn('SECRET NAME', str(dict(self.client.session)))

    @patch('dashboard.wallet_views.api.call')
    def test_false_and_malformed_release_never_render_or_cache(self, api):
        for verification in (dict(passed(), verified=False), {}, None, 'true',
                             dict(passed(), verified='true'), dict(passed(), proofValid=False)):
            with self.subTest(verification=verification):
                api.return_value = {'bundle': bundle(), 'verification': verification}
                response = self.client.post('/verify/'+'a'*64+'/')
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'Service verification passed')
                self.assertNotContains(response, 'CGPA at least 8.5')
                self.assertFalse(self.client.session.get('released_proofs'))

    @patch('dashboard.wallet_views.api.call')
    def test_malformed_success_bundle_fails_closed(self, api):
        for bad in (None, {}, 'bundle', dict(bundle(), claims=[]), dict(bundle(), leafCount=True)):
            with self.subTest(bundle=bad):
                api.return_value = {'bundle': bad, 'verification': passed()}
                response = self.client.post('/verify/'+'a'*64+'/')
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'Service verification passed')
                self.assertFalse(self.client.session.get('released_proofs'))

    @patch('dashboard.wallet_views.api.call')
    def test_export_rejects_truthy_or_incomplete_verification(self, api):
        b = bundle()
        for result in ({'verified': 'true'}, {'verified': True}, None, [], passed() | {'current': False}):
            session = self.client.session
            session['released_proofs'] = {b['presentation']['grantId']: proof_cache.seal(b)}
            session.save()
            api.return_value = result
            response = self.client.get('/proof-download/'+b['presentation']['grantId']+'/')
            self.assertEqual(response.status_code, 410)
            self.assertNotContains(response, 'CGPA at least 8.5', status_code=410)
            self.assertFalse(self.client.session.get('released_proofs'))

    @override_settings(TRUSTED_DEPLOYMENT={'contract': '0x'+'12'*20, 'operator': '0x'+'34'*20, 'chainId': 1337})
    @patch('dashboard.wallet_views.api.call')
    def test_pins_are_local_and_custom_claim_is_explicit(self, api):
        api.return_value = {'bundle': bundle(), 'verification': passed()}
        response = self.client.post('/verify/'+'a'*64+'/')
        self.assertContains(response, 'Service verification passed')
        self.assertContains(response, 'Holder-authored statement')
        self.assertContains(response, 'custom.eligibility')
        self.assertContains(response, 'boolean')
        self.assertContains(response, '0x'+'12'*20)
        self.assertNotContains(response, 'Platform-derived threshold')
        api.assert_called_once_with('POST', '/api/public/disclosures/'+'a'*64+'/open')

    @patch('dashboard.wallet_views.api.call')
    def test_recognized_derived_claim_keeps_bound_metadata(self, api):
        b = bundle()
        b['claims'][0]['leaf'].update(path='education.cgpa_at_least_8_5', derivedFrom='education.cgpa')
        api.return_value = {'bundle': b, 'verification': passed()}
        response = self.client.post('/verify/'+'a'*64+'/')
        self.assertContains(response, 'Platform-derived threshold')
        self.assertContains(response, 'education.cgpa_at_least_8_5')
        self.assertContains(response, 'education.cgpa')

    @patch('dashboard.wallet_views.api.call')
    def test_noncanonical_fields_and_assurance_mismatch_never_render_or_export(self, api):
        changes = [
            lambda b: b['claims'][0]['leaf'].update(value='TRUE'),
            lambda b: b['claims'][0]['leaf'].update(type='decimal', value='09.170'),
            lambda b: b['claims'][0]['leaf'].update(type='date', value='2026-02-30'),
            lambda b: b['claims'][0]['leaf'].update(path='../x'),
            lambda b: b['claims'][0]['leaf'].update(derivedFrom='../source'),
            lambda b: b['presentation'].update(grantId='-'*36),
            lambda b: b['provenance'].update(level='FIRST_SEEN_TRACKED'),
        ]
        for change in changes:
            b = copy.deepcopy(bundle())
            change(b)
            api.return_value = {'bundle': b, 'verification': passed()}
            response = self.client.post('/verify/'+'a'*64+'/')
            self.assertNotContains(response, 'Service verification passed')
            self.assertFalse(self.client.session.get('released_proofs'))
            key = b['presentation']['grantId']
            session = self.client.session
            session['released_proofs'] = {key: proof_cache.seal(b)}
            session.save()
            api.return_value = passed()
            response = self.client.get('/proof-download/'+key+'/')
            self.assertEqual(response.status_code, 404)
            self.assertFalse(self.client.session.get('released_proofs'))

    def test_legacy_suggestion_copy_is_removed_on_any_request(self):
        session = self.client.session
        session['claim_suggestions'] = {'claims': [{'value': 'SECRET'}]}
        session.save()
        self.client.get('/login/')
        self.assertNotIn('claim_suggestions', self.client.session)

    def test_migration_cleans_expired_and_active_legacy_session_rows(self):
        from datetime import timedelta
        from django.utils import timezone
        from django.contrib.sessions.models import Session
        from django.contrib.sessions.backends.db import SessionStore
        from django.apps import apps
        from django.db import connection
        codec = SessionStore()
        for days, key in ((-1, 'expired-fixture'), (1, 'active-fixture')):
            Session.objects.create(session_key=key, expire_date=timezone.now()+timedelta(days=days),
                                   session_data=codec.encode({'claim_suggestions': {'value':'SECRET'}, 'keep':'value'}))
        migration = importlib.import_module('dashboard.migrations.0001_remove_session_suggestions')
        migration.purge_suggestions(apps, connection.schema_editor())
        for row in Session.objects.all():
            self.assertNotIn('claim_suggestions', row.get_decoded())
            self.assertEqual(row.get_decoded()['keep'], 'value')
