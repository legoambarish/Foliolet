"""Real Docker acceptance: fictional files only; never contacts the DigiLocker portal.

Reuses the existing intake, failure, local-AI and independent-verifier acceptance
gates. Private checkpoints stay in the Docker test volume; reports exclude secrets.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid
import requests

ROOT=Path('/app')
spec=importlib.util.spec_from_file_location('intake_acceptance',ROOT/'tools/test-intake-live.py')
live=importlib.util.module_from_spec(spec);spec.loader.exec_module(live)
HTTP=requests.Session();HTTP.trust_env=False
CHECKPOINT=ROOT/'.local-data/docker-tests/persistence-private.json'

def run(script):
    print('RUN',Path(script).name,flush=True)
    subprocess.run([sys.executable,str(ROOT/script)],check=True)

def wait_for(function, message, seconds=50):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        value=function()
        if value:return value
        time.sleep(.5)
    raise AssertionError(message)

def managed_intake():
    auth=live.account()
    login=HTTP.get(live.UI+'/login/',timeout=10)
    token=HTTP.cookies.get('csrftoken')
    assert token and login.status_code==200,'Django login/CSRF not ready'
    logged=HTTP.post(live.UI+'/login/',data={'csrfmiddlewaretoken':token,'username':auth[0],'password':auth[1]},timeout=20)
    assert logged.status_code==200 and logged.url.rstrip('/')==live.UI
    page=HTTP.get(live.UI+'/wallet/enroll/',timeout=15)
    live.check('data-managed="yes"' in page.text and 'start-digilocker-watcher.ps1' not in page.text,
               'Docker intake needs no pairing-file or terminal workflow')
    missing=HTTP.post(live.UI+'/intake/pair/',data={'consent':'yes'},timeout=10)
    live.check(missing.status_code==403,'Real Docker Django pairing rejects missing CSRF')
    csrf=HTTP.cookies.get('csrftoken')
    refused=HTTP.post(live.UI+'/intake/pair/',data={'csrfmiddlewaretoken':csrf},timeout=15)
    live.check(refused.status_code==400,'Running watcher cannot arm without explicit holder consent')
    before=Path('/test-intake')/('preexisting-'+uuid.uuid4().hex+'.txt')
    before.write_text('Fictional pre-existing file; must not be imported.')
    time.sleep(1.2)
    pair=HTTP.post(live.UI+'/intake/pair/',data={'csrfmiddlewaretoken':csrf,'folder':'/etc','consent':'yes'},timeout=20)
    assert pair.status_code==200,'Managed pairing failed'
    paired=pair.json()
    live.check(set(paired)=={'managed','sessionId'} and paired['managed'],
               'Managed consent returns no watcher capability to the browser')
    sessions=lambda:live.request('GET','/api/wallet/intake/sessions',auth)
    wait_for(lambda:sessions()[0]['connected'],'Container companion did not connect')
    live.check(sessions()[0]['folder']=='/host/intake/documents-inbox',
               'Posted arbitrary folder is ignored; only the dedicated read-only bind is armed')
    # The production watcher has RO access; only this explicitly requested test service writes test fixtures.
    nested=Path('/test-intake')/('fictional-'+uuid.uuid4().hex)/'semester';nested.mkdir(parents=True)
    content=(ROOT/'.local-data/ocr-p0/fixtures/native-table.pdf').read_bytes()
    partial=nested/'marks.pdf.crdownload';partial.write_bytes(content[:500]);time.sleep(3)
    live.check(sessions()[0]['imported']==0,'Pre-existing files and partial downloads stay out of Docker intake')
    partial.write_bytes(content);partial.rename(nested/'marks.pdf')
    row=wait_for(lambda:(rows[0] if (rows:=sessions())[0]['imported'] else None),'Mac bind reconciliation failed',65)
    live.check(row['imported']==1,'Nested completed host download imports through the included companion')
    cid=row['documents'][0]['id']
    result=live.analysis(auth,cid)
    live.check(result['report']['diagnostics']['supported']==19 and result['issuer']=='NOT_VERIFIED',
               'Docker PDFBox retains all 19 supported table facts without upgrading issuer assurance')
    original=live.request('GET','/api/wallet/documents/'+cid+'/file',auth).content
    live.check(original==content==(nested/'marks.pdf').read_bytes(),'Mounted download and encrypted-vault original match byte for byte')
    end=HTTP.post(live.UI+'/intake/sessions/'+paired['sessionId']+'/stop/',data={'csrfmiddlewaretoken':csrf},timeout=15)
    assert end.status_code==200
    wait_for(lambda:not sessions()[0]['active'],'Stop did not revoke intake')
    (nested/'after-stop.txt').write_text('Fictional after-stop file must not be imported.')
    time.sleep(7)
    live.check(sessions()[0]['imported']==1,'Stopping consent prevents subsequent host-folder imports')
    saved=live.confirm(auth,cid,live.claims(result))
    live.check(saved['intake']['lineage']=='SUGGESTIONS_UNMODIFIED','Docker exact native facts retain their server-side baseline')

def persistence(write):
    if write:
        auth=live.account()
        content=b'Math: 91\nName: Fictional Docker Persistence\n'
        cid=live.request('POST','/api/wallet/documents',auth,files={'file':('synthetic-persistence.txt',content)},
            data={'displayName':'Fictional restart acceptance','category':'Other'})['id']
        result=live.analysis(auth,cid)
        live.confirm(auth,cid,live.claims(result))
        doc=live.request('POST','/api/wallet/documents/'+cid+'/anchor',auth)
        CHECKPOINT.parent.mkdir(exist_ok=True,parents=True)
        CHECKPOINT.write_text(json.dumps({'auth':auth,'id':cid,'hash':hashlib.sha256(content).hexdigest(),
            'keyHash':hashlib.sha256((ROOT/'.local-data/development-relay.key').read_bytes()).hexdigest(),
            'pins':json.loads((ROOT/'.local-data/trusted-deployment.json').read_text())}))
        CHECKPOINT.chmod(0o600)
        live.check(doc['status']=='ACTIVE','Anchored fictional state recorded before Docker stop/rebuild')
    else:
        state=json.loads(CHECKPOINT.read_text());auth=tuple(state['auth']);cid=state['id']
        doc=live.request('GET','/api/wallet/documents/'+cid,auth)
        original=live.request('GET','/api/wallet/documents/'+cid+'/file',auth).content
        live.check(doc['status']=='ACTIVE' and hashlib.sha256(original).hexdigest()==state['hash'],
                   'Restart retains the database, vault encryption and original bytes')
        live.check(hashlib.sha256((ROOT/'.local-data/development-relay.key').read_bytes()).hexdigest()==state['keyHash']
                   and json.loads((ROOT/'.local-data/trusted-deployment.json').read_text())==state['pins'],
                   'Restart preserves the EVM signer and independent trust pins')
        claim=next(f for f in doc['claims'] if f['path']=='education.math')
        _,route=live.share(auth,cid,claim['id'])
        bundle=live.request('POST',route)['bundle'];live.independent(bundle)
        live.check(True,'Retained chain commitment verifies independently after Docker restart')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--persistence-write',action='store_true');parser.add_argument('--persistence-read',action='store_true')
    args=parser.parse_args()
    password=Path('/run/foliolet-secrets/postgres-password').read_text().strip()
    # Generated password is URL-safe; neither environment nor DSNs are printed.
    os.environ.update({'INTAKE_TEST_DSN':f'host=postgres dbname=foliolet user=foliolet password={password}',
        'INTAKE_TEST_ADMIN_DSN':f'host=postgres dbname=postgres user=foliolet password={password}',
        'INTAKE_TEST_JDBC_PREFIX':'jdbc:postgresql://postgres:5432/','INTAKE_TEST_DB_USER':'foliolet',
        'INTAKE_TEST_DB_PASSWORD':password,'INTAKE_FAILURE_PORT':'8097','FOLIOLET_TEST_JAR':'/app/service.jar',
        'SPRING_CONFIG_ADDITIONAL_LOCATION':'file:/app/containers/application.yaml'})
    live.DSN=os.environ['INTAKE_TEST_DSN']
    if args.persistence_write or args.persistence_read:
        persistence(args.persistence_write);return
    run('tools/make-intake-fixtures.py');run('tools/make-ocr-benchmark.py')
    managed_intake()
    report=ROOT/'.local-data/intake-tests/docker-managed-results.json'
    report.write_text(json.dumps({'checks':live.checks,'count':len(live.checks),'synthetic':True},indent=2))
    run('tools/test-intake-live.py')
    run('tools/test-intake-failures.py')
    print('Docker acceptance complete. Genuine issuer documents, hardware NFC and real macOS filesystem delivery are separate checks.',flush=True)

if __name__=='__main__':main()
