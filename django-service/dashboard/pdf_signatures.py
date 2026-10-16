"""Bounded subprocess bridge for private PDF signature inspection."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

MAX_BYTES = 20*1024*1024
_slots = threading.BoundedSemaphore(1)


def inspect_pdf(data):
    if not isinstance(data,bytes) or len(data)>MAX_BYTES:
        return {'status':'UNSUPPORTED_OR_OVERSIZED','issuerVerified':False,'signatures':[]}
    source_hash=hashlib.sha256(data).hexdigest()
    def failed(status):
        return {'schema':'foliolet-pdf-signature-inspection-v1','sourceSha256':source_hash,
                'status':status,'issuerVerified':False,'offline':True,'signatures':[]}
    if not data.startswith(b'%PDF-'):return failed('NOT_A_SUPPORTED_PDF')
    if not _slots.acquire(blocking=False):return failed('SIGNATURE_INSPECTOR_BUSY')
    try:
        with tempfile.TemporaryDirectory(prefix='foliolet-signature-') as folder:
            path=Path(folder)/'original.pdf'
            descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(descriptor,'wb') as output:output.write(data)
            env={k:v for k,v in os.environ.items() if k.upper() in ('PATH','SYSTEMROOT','WINDIR','TEMP','TMP')}
            worker=Path(__file__).with_name('signature_worker.py').resolve()
            try:
                result=subprocess.run([sys.executable,'-I',str(worker),str(path)],cwd=folder,env=env,
                    stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=25,check=False)
            except subprocess.TimeoutExpired:return failed('SIGNATURE_INSPECTION_TIMEOUT')
            if result.returncode or len(result.stdout)>32768:return failed('SIGNATURE_INSPECTOR_UNAVAILABLE')
            try:report=json.loads(result.stdout)
            except (ValueError,UnicodeError):return failed('INVALID_SIGNATURE_INSPECTION_RESULT')
            if not isinstance(report,dict) or report.get('sourceSha256')!=source_hash:
                return failed('SIGNATURE_SOURCE_BINDING_FAILED')
            # This feature has no issuer-authority policy and cannot change chain assurance.
            if report.get('issuerVerified') is not False:return failed('UNSUPPORTED_ISSUER_ASSURANCE')
            return report
    finally:_slots.release()
