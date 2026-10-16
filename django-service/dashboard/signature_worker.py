"""Read-only isolated PDF signature inspector. No issuer authority is inferred.

Run only through pdf_signatures.inspect_pdf: bounded input, CPU, memory and time.
The empty explicit trust store is intentional: embedded certificates are evidence,
not trust anchors. A valid self-signature is not an institution's endorsement.
"""
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


def inspect_bytes(data):
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature
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
        entry={'index':index+1,'issuerVerified':False}
        subfilter=str(signature.sig_object.get('/SubFilter',''))
        if subfilter not in ('/adbe.pkcs7.detached','/ETSI.CAdES.detached'):
            report['signatures'].append(dict(entry,status='UNSUPPORTED_SIGNATURE_FORMAT'))
            continue
        try:
            # Never load OS trust roots or trust a certificate merely because it is embedded.
            context=ValidationContext(trust_roots=[],allow_fetching=False,revocation_mode='hard-fail')
            status=validate_pdf_signature(signature, signer_validation_context=context,
                                          ts_validation_context=context)
            intact=bool(status.intact); valid=bool(status.valid)
            whole=status.coverage == SignatureCoverageLevel.ENTIRE_FILE
            entry.update(digestIntact=intact,signatureMathValid=valid,entireCurrentFile=whole,
                         certificatePathTrusted=bool(status.trusted),
                         coverage=status.coverage.name if status.coverage else 'UNKNOWN',
                         signerCertificateSha256=hashlib.sha256(signature.signer_cert.dump()).hexdigest(),
                         status='SIGNATURE_VALID_BUT_ISSUER_UNTRUSTED' if intact and valid and whole
                                else 'SIGNATURE_OR_CURRENT_FILE_CHECK_FAILED')
        except Exception as error:
            # Keep certificate names, source data and parser diagnostics out of responses/logs.
            entry.update(status='SIGNATURE_CHECK_INCOMPLETE',errorType=type(error).__name__)
        report['signatures'].append(entry)
    report['status']='INSPECTED_NOT_ISSUER_VERIFIED'
    return report


def main():
    logging.disable(logging.CRITICAL)
    # Defence in depth in addition to allow_fetching=False. This is not an OS sandbox.
    socket.create_connection=deny_network
    socket.socket.connect=deny_network
    socket.socket.connect_ex=deny_network
    if os.name=='posix':
        import resource
        resource.setrlimit(resource.RLIMIT_CPU,(20,20))
        resource.setrlimit(resource.RLIMIT_AS,(768*1024*1024,768*1024*1024))
        resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    path=Path(sys.argv[1])
    with path.open('rb') as source:data=source.read(MAX_BYTES+1)
    try: result=inspect_bytes(data)
    except Exception as error:
        result={'schema':'foliolet-pdf-signature-inspection-v1','sourceSha256':hashlib.sha256(data).hexdigest(),
                'status':'MALFORMED_OR_UNSUPPORTED_PDF','issuerVerified':False,'offline':True,
                'errorType':type(error).__name__,'signatures':[]}
    sys.stdout.write(json.dumps(result,ensure_ascii=True))

if __name__=='__main__':main()
