"""Read-only isolated PDF signature inspector. No issuer authority is inferred.

The empty explicit trust store is intentional: embedded certificates are evidence,
not trust anchors. A valid self-signature is not an institution's endorsement.
"""
import asyncio
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import socket
import sys
from datetime import datetime, timezone

MAX_BYTES = 20 * 1024 * 1024


def deny_network(*args, **kwargs):
    raise PermissionError('PDF signature inspection is offline')


def inspect_bytes(data, loop):
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import async_validate_pdf_signature
    from pyhanko.sign.validation.status import SignatureCoverageLevel
    from pyhanko_certvalidator import ValidationContext
    report = {'schema':'foliolet-pdf-signature-inspection-v1',
              'sourceSha256':hashlib.sha256(data).hexdigest(),
              'checkedAt':datetime.now(timezone.utc).isoformat(),
              'issuerVerified':False,'offline':True,'trustPolicy':'NO_IMPLICIT_TRUST_ANCHORS',
              'revocation':'NOT_ESTABLISHED','signatures':[]}
    if not data.startswith(b'%PDF-') or len(data)>MAX_BYTES:
        return dict(report,status='UNSUPPORTED_OR_OVERSIZED')
    reader=PdfFileReader(io.BytesIO(data), strict=True)
    if reader.encrypted:
        return dict(report,status='ENCRYPTED_PDF_UNSUPPORTED')
    signatures=reader.embedded_regular_signatures
    if not signatures:return dict(report,status='UNSIGNED')
    if len(signatures)>8:return dict(report,status='SIGNATURE_COUNT_LIMIT')
    for index, signature in enumerate(signatures):
        entry={'index':index+1,'issuerVerified':False,'digestIntact':None,
               'signatureMathValid':None,'entireCurrentFile':None,'certificatePathTrusted':None}
        subfilter=str(signature.sig_object.get('/SubFilter',''))
        if subfilter not in ('/adbe.pkcs7.detached','/ETSI.CAdES.detached'):
            report['signatures'].append(dict(entry,status='UNSUPPORTED_SIGNATURE_FORMAT'))
            continue
        stage='VALIDATION_CONTEXT'
        try:
            # hard-fail with no CRLs and no fetching is an invalid library context.
            # This context inspects signature mathematics, NOT issuer assurance.
            # Missing revocation remains NOT_ESTABLISHED and an empty explicit
            # root store plus issuerVerified=False prevents any trust promotion.
            context=ValidationContext(trust_roots=[],allow_fetching=False,revocation_mode='soft-fail')
            stage='CRYPTOGRAPHIC_VALIDATION'
            status=loop.run_until_complete(async_validate_pdf_signature(signature,
                signer_validation_context=context,ts_validation_context=context))
            stage='RESULT_CLASSIFICATION'
            intact=bool(status.intact); valid=bool(status.valid)
            whole=status.coverage == SignatureCoverageLevel.ENTIRE_FILE
            entry.update(digestIntact=intact,signatureMathValid=valid,entireCurrentFile=whole,
                         certificatePathTrusted=bool(status.trusted),
                         coverage=status.coverage.name if status.coverage else 'UNKNOWN',
                         signerCertificateSha256=hashlib.sha256(signature.signer_cert.dump()).hexdigest(),
                         status='SIGNATURE_VALID_BUT_ISSUER_UNTRUSTED' if intact and valid and whole
                                else 'SIGNATURE_OR_CURRENT_FILE_CHECK_FAILED')
        except Exception as error:
            entry.update(status='SIGNATURE_CHECK_INCOMPLETE',errorType=type(error).__name__,errorStage=stage)
        report['signatures'].append(entry)
    report['status']='INSPECTED_NOT_ISSUER_VERIFIED'
    return report


def main():
    logging.disable(logging.CRITICAL)
    if os.name=='posix':
        import resource
        resource.setrlimit(resource.RLIMIT_CPU,(20,20))
        resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    # The Windows event loop creates an internal socket pair. Create it before
    # denying connection calls, not while processing attacker-controlled source.
    loop=asyncio.new_event_loop()
    socket.create_connection=deny_network
    socket.socket.connect=deny_network
    socket.socket.connect_ex=deny_network
    path=Path(sys.argv[1])
    with path.open('rb') as source:data=source.read(MAX_BYTES+1)
    try:
        result=inspect_bytes(data,loop)
    except Exception as error:
        result={'schema':'foliolet-pdf-signature-inspection-v1','sourceSha256':hashlib.sha256(data).hexdigest(),
                'status':'MALFORMED_OR_UNSUPPORTED_PDF','issuerVerified':False,'offline':True,
                'errorType':type(error).__name__,'signatures':[]}
    finally:loop.close()
    sys.stdout.write(json.dumps(result,ensure_ascii=True))

if __name__=='__main__':main()
