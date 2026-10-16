"""Real fictional PDF/CMS signatures, not mocked cryptographic success."""
import hashlib
import io
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase, RequestFactory, Client, override_settings
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from asn1crypto import x509 as asn1_x509, keys
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import signers
from pyhanko_certvalidator.registry import SimpleCertificateStore
from dashboard.pdf_signatures import inspect_pdf, MAX_BYTES
from dashboard import signature_views


def fictional_pdf():
    stream=b'BT /F1 12 Tf 40 100 Td (Fictional statement: 91 marks) Tj ET'
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
    data=bytearray(b'%PDF-1.7\n');offsets=[0]
    for i,obj in enumerate(objects,1):
        offsets.append(len(data));data.extend(str(i).encode()+b' 0 obj\n'+obj+b'\nendobj\n')
    xref=len(data);data.extend(b'xref\n0 6\n0000000000 65535 f \n')
    for offset in offsets[1:]:data.extend(f'{offset:010d} 00000 n \n'.encode())
    data.extend(f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(data)


def signed_fixture():
    private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Fictional Untrusted Test Signer')])
    now=datetime.now(timezone.utc)
    certificate=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(private.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
        .add_extension(x509.KeyUsage(digital_signature=True,content_commitment=True,key_encipherment=False,data_encipherment=False,
            key_agreement=False,key_cert_sign=False,crl_sign=False,encipher_only=False,decipher_only=False),critical=True)
        .sign(private,hashes.SHA256()))
    signer=signers.SimpleSigner(signing_cert=asn1_x509.Certificate.load(certificate.public_bytes(serialization.Encoding.DER)),
        signing_key=keys.PrivateKeyInfo.load(private.private_bytes(serialization.Encoding.DER,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())),
        cert_registry=SimpleCertificateStore())
    output=signers.sign_pdf(IncrementalPdfFileWriter(io.BytesIO(fictional_pdf())),
        signature_meta=signers.PdfSignatureMetadata(field_name='FictionalSignature'),signer=signer)
    return output.getvalue()


class PdfSignatureTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass();cls.signed=signed_fixture()

    def test_unsigned_pdf_is_not_falsely_called_signed_or_issuer_verified(self):
        result=inspect_pdf(fictional_pdf())
        self.assertEqual(result['status'],'UNSIGNED')
        self.assertIs(result['issuerVerified'],False)

    def test_genuine_signature_math_is_separate_from_unknown_issuer(self):
        result=inspect_pdf(self.signed)
        self.assertEqual(result['status'],'INSPECTED_NOT_ISSUER_VERIFIED',result)
        self.assertEqual(len(result['signatures']),1)
        signature=result['signatures'][0]
        self.assertTrue(signature['digestIntact'],result)
        self.assertTrue(signature['signatureMathValid'],result)
        self.assertTrue(signature['entireCurrentFile'],result)
        self.assertFalse(signature['certificatePathTrusted'])
        self.assertFalse(result['issuerVerified'])
        self.assertEqual(result['sourceSha256'],hashlib.sha256(self.signed).hexdigest())

    def test_changed_signed_statement_is_rejected(self):
        tampered=self.signed.replace(b'91 marks',b'95 marks',1)
        self.assertNotEqual(tampered,self.signed)
        result=inspect_pdf(tampered)
        self.assertFalse(result['issuerVerified'])
        self.assertTrue(result['signatures'])
        self.assertFalse(result['signatures'][0].get('digestIntact',False),result)

    def test_arbitrary_and_oversized_inputs_never_reach_parser_success(self):
        for data in (b'not a PDF', b'%PDF-broken', b'%PDF-'+b'x'*MAX_BYTES):
            result=inspect_pdf(data)
            self.assertFalse(result['issuerVerified'])
            self.assertNotEqual(result['status'],'INSPECTED_NOT_ISSUER_VERIFIED')

    @patch('dashboard.pdf_signatures.subprocess.run')
    def test_source_substitution_and_issuer_promotion_are_rejected(self, run):
        data=fictional_pdf()
        for body in ({'sourceSha256':'0'*64,'issuerVerified':False},
                     {'sourceSha256':hashlib.sha256(data).hexdigest(),'issuerVerified':True}):
            run.return_value=SimpleNamespace(returncode=0,stdout=json.dumps(body).encode())
            result=inspect_pdf(data)
            self.assertFalse(result['issuerVerified'])
            self.assertIn(result['status'],('SIGNATURE_SOURCE_BINDING_FAILED','UNSUPPORTED_ISSUER_ASSURANCE'))

    @patch('dashboard.pdf_signatures.subprocess.run')
    def test_child_receives_no_application_credentials_or_proxy_environment(self, run):
        import os
        data=fictional_pdf();run.return_value=SimpleNamespace(returncode=1,stdout=b'')
        with patch.dict(os.environ,{'BLOCKCHAIN_PRIVATE_KEY':'private','HTTPS_PROXY':'http://proxy.invalid','OPENROUTER_API_KEY':'private'}):
            result=inspect_pdf(data)
        env=run.call_args.kwargs['env']
        self.assertNotIn('BLOCKCHAIN_PRIVATE_KEY',env);self.assertNotIn('HTTPS_PROXY',env);self.assertNotIn('OPENROUTER_API_KEY',env)
        self.assertEqual(result['status'],'SIGNATURE_INSPECTOR_UNAVAILABLE')

    def test_private_view_requires_local_authenticated_request(self):
        for remote,auth in (('203.0.113.1',['u','p']),('127.0.0.1',None)):
            request=RequestFactory().post('/wallet/00000000-0000-4000-8000-000000000001/signature/',REMOTE_ADDR=remote)
            request.session={'sb_auth':auth} if auth else {}
            with patch('dashboard.signature_views.api.call') as backend:
                response=signature_views.inspect(request,'00000000-0000-4000-8000-000000000001')
                self.assertIn(response.status_code,(401,404));backend.assert_not_called()

    def test_csrf_free_post_is_rejected_before_source_download(self):
        with patch('dashboard.signature_views.api.call') as backend:
            response=Client(enforce_csrf_checks=True).post('/wallet/00000000-0000-4000-8000-000000000001/signature/')
            self.assertEqual(response.status_code,403);backend.assert_not_called()
