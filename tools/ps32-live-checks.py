"""Real acceptance against fresh job-owned services only; never a personal runtime."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import requests

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('wallet_live',ROOT/'tools/test-live-workflow.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
checks=[]


def check(condition,name):
    if not condition:raise AssertionError(name)
    checks.append(name);print('PASS '+name,flush=True)


def wait_ready(url,timeout=90):
    start=time.monotonic()
    while time.monotonic()-start<timeout:
        try:
            if requests.get(url,timeout=2).status_code==200:return time.monotonic()-start
        except requests.RequestException:pass
        time.sleep(.5)
    raise AssertionError('Disposable service did not become ready')


def stopped(pid):
    os.kill(pid,signal.SIGTERM)
    for _ in range(100):
        try:os.kill(pid,0)
        except ProcessLookupError:return
        time.sleep(.1)


def rejected_verification(bundle):
    try:
        response=requests.post(w.BASE+'/api/public/verify-bundle',json=bundle,timeout=(3,45))
        return response.status_code!=200 or response.json().get('verified') is False
    except requests.Timeout:raise AssertionError('Verification timed out instead of returning fail-closed')


def main():
    if os.environ.get('GITHUB_ACTIONS')!='true' or w.BASE!='http://127.0.0.1:8088':
        raise SystemExit('Restricted to the isolated GitHub Actions fixture')
    container=os.environ['PS32_POSTGRES_CONTAINER']
    if not re.fullmatch(r'[a-f0-9]{12,64}',container):raise ValueError('Invalid owned container')
    info=json.loads(subprocess.check_output(['docker','inspect',container]))[0]
    if 'POSTGRES_DB=wallet_intake_demo' not in info['Config']['Env']:raise ValueError('Unrelated database')
    backend_pid,evm_pid=int(os.environ['PS32_BACKEND_PID']),int(os.environ['PS32_EVM_PID'])
    children,handles,database_stopped=[],[],False
    timings={}
    try:
        subprocess.run(['node','tools/ps32-signature-ui.cjs'],cwd=ROOT,check=True,timeout=240)
        check(True,'Actual browser inspects unsigned, signed-untrusted and tampered originals without external requests')
        owner=w.account()
        content=b'Name: Fictional Resilience Student\nCGPA: 9.17\nInstitution: Fictional Institute\nCourse: Engineering\nDate of birth: 2004-01-02\n'
        document=w.commit(owner,w.upload(owner,content));grant=w.share(owner,document)
        bundle=w.call('POST',w.token_path(grant))['bundle']
        check(w.call('POST','/api/public/verify-bundle',json=bundle)['verified'],'Real pinned EVM proof passes before dependency faults')
        for origin in ('https://outside.invalid','null',w.UI):
            response=requests.get(w.BASE+'/api/wallet/documents',auth=owner,headers={'Origin':origin},timeout=10)
            check(response.status_code==403 and response.json().get('code')=='PRIVATE_API_ORIGIN','Private HTTP Basic API rejects browser Origin '+('opaque' if origin=='null' else 'present'))
        check(isinstance(w.call('GET','/api/wallet/documents',owner),list),'Native authenticated bridge remains usable')
        subprocess.run(['docker','stop','--time','10',container],check=True,stdout=subprocess.DEVNULL);database_stopped=True
        start=time.monotonic();check(rejected_verification(bundle),'Database interruption never yields a verified proof')
        timings['databaseFailureResponseSeconds']=time.monotonic()-start
        subprocess.run(['docker','start',container],check=True,stdout=subprocess.DEVNULL);database_stopped=False
        for _ in range(60):
            if subprocess.run(['docker','exec',container,'pg_isready','-U','wallet','-d','wallet_intake_demo'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
            time.sleep(.5)
        check(w.call('POST','/api/public/verify-bundle',json=bundle)['verified'],'Same proof succeeds after original database resumes')
        key_hash=hashlib.sha256((ROOT/'.local-data/development-relay.key').read_bytes()).hexdigest()
        stopped(evm_pid)
        start=time.monotonic();check(rejected_verification(bundle),'Actual EVM outage fails closed, never uses stale successful verification')
        timings['evmFailureResponseSeconds']=time.monotonic()-start
        log=(ROOT/'.local-data/ps32-private/evm-restart.log').open('w');handles.append(log)
        evm=subprocess.Popen(['node','tools/digilocker-evm.cjs'],cwd=ROOT,env=os.environ,stdout=log,stderr=log);children.append(evm)
        for _ in range(60):
            try:
                if requests.post(w.RPC,json={'jsonrpc':'2.0','id':1,'method':'eth_chainId','params':[]},timeout=2).ok:break
            except requests.RequestException:pass
            time.sleep(.5)
        check(w.call('POST','/api/public/verify-bundle',json=bundle)['verified'],'Original chain restart preserves contract state and proof validity')
        check(hashlib.sha256((ROOT/'.local-data/development-relay.key').read_bytes()).hexdigest()==key_hash,'EVM restart preserves the signing identity')
        session=requests.Session();page=session.get(w.UI+'/login/',timeout=10)
        csrf=re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"',page.text).group(1)
        logged=session.post(w.UI+'/login/',data={'csrfmiddlewaretoken':csrf,'username':owner[0],'password':owner[1]},headers={'Origin':w.UI},timeout=20)
        check(logged.status_code==200 and '/login/' not in logged.url,'Real Django login works with encrypted database sessions')
        inspect_code="""from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.db import SessionStore
from django.core import signing
class Raw:
 def loads(self,data):return data
rows=list(Session.objects.all());assert rows
for row in rows:
 raw=signing.loads(row.session_data,salt=SessionStore().key_salt,serializer=Raw)
 assert raw.startswith(b'FSES1:'), 'Unencrypted newly written session'
 assert isinstance(row.get_decoded(),dict)
print('Encrypted envelopes and authenticated JSON decoding confirmed')
"""
        subprocess.run(['python','manage.py','shell','-c',inspect_code],cwd=ROOT/'django-service',check=True)
        check(True,'Actual Django session database contains encrypted authenticated envelopes')
        vault_key=ROOT/'.local-data/vault.key';before=hashlib.sha256(vault_key.read_bytes()).hexdigest()
        stopped(backend_pid)
        env=dict(os.environ,BLOCKCHAIN_PRIVATE_KEY=(ROOT/'.local-data/development-relay.key').read_text().strip())
        log=(ROOT/'.local-data/ps32-private/backend-restart.log').open('w');handles.append(log)
        backend=subprocess.Popen(['java','-Xmx768m','-jar','target/dms-0.0.1-SNAPSHOT.jar'],cwd=ROOT/'spring-boot-service',env=env,stdout=log,stderr=log);children.append(backend)
        timings['backendRestartSeconds']=wait_ready(w.BASE+'/api/public/network')
        check(w.call('POST','/api/public/verify-bundle',json=bundle)['verified'],'Packaged backend restart preserves existing proof and grant policy')
        original=requests.get(w.BASE+f"/api/wallet/documents/{document['id']}/file",auth=owner,timeout=20)
        check(original.status_code==200 and original.content==content,'Encrypted original remains byte-exact after database, chain and backend restarts')
        check(hashlib.sha256(vault_key.read_bytes()).hexdigest()==before,'Backend restart preserves the vault encryption key')
        page=session.get(w.UI+'/',timeout=20)
        check(page.status_code==200 and '/login/' not in page.url,'Existing holder session survives backend restart')
    finally:
        if database_stopped:subprocess.run(['docker','start',container],stdout=subprocess.DEVNULL)
        for process in reversed(children):
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=15)
                except subprocess.TimeoutExpired:process.kill();process.wait()
        for handle in handles:handle.close()
        (ROOT/'audit-evidence/resilience-results.json').write_text(json.dumps({'checks':checks,'timings':timings},indent=2))
    print(json.dumps({'passed':len(checks),'timings':timings},indent=2))

if __name__=='__main__':main()
