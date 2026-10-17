"""Real API/EVM/vault acceptance, plus fresh Django profiles against that API.

Only fictional facts; optional local --reference image is never exported or sent
to cloud. Django Client exercises real middleware/CSRF/templates and real Spring
HTTP, without a tunnel, server restart or mocked backend. HTML stays ignored.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'.local-data/p0/status-live'
OUT.mkdir(parents=True, exist_ok=True)
API = os.environ.get('INTAKE_TEST_API', 'http://127.0.0.1:8089')
RPC = os.environ.get('INTAKE_TEST_RPC', 'http://127.0.0.1:8558')
assert API.startswith('http://127.0.0.1:') and RPC.startswith('http://127.0.0.1:')
HTTP = requests.Session(); HTTP.trust_env = False
checks = []
def check(ok, name):
    assert ok, name
    checks.append(name)
    print('PASS', name, flush=True)
def call(method, path, auth=None, **kwargs):
    response = HTTP.request(method, API+path, auth=auth, timeout=65, **kwargs)
    assert response.ok, f'{method} failed with HTTP {response.status_code}'
    return response.json() if 'application/json' in response.headers.get('Content-Type','') else {}
def profile(name):
    public = name == 'receiver'
    origin = 'https://p0-fixture.trycloudflare.com'
    os.environ.update(SPRING_BOOT_API_BASE_URL=API, FOLIOLET_SHARE_MODE='local',
        DJANGO_SETTINGS_MODULE='hermes.receiver_settings' if public else 'hermes.settings',
        FOLIOLET_PUBLIC_BASE_URL=origin, FOLIOLET_RECEIVER_INSTANCE='p0-fixture')
    sys.path.insert(0, str(ROOT/'django-service'))
    import django
    django.setup()
    from django.core.management import call_command
    from django.test import Client, override_settings
    call_command('migrate', verbosity=0, interactive=False)
    secret = json.loads((OUT/'checkpoint.json').read_text())
    host = 'p0-fixture.trycloudflare.com' if public else 'testserver'
    client = Client(enforce_csrf_checks=True)
    path = '/verify/'+secret['token']+'/'
    with override_settings(ALLOWED_HOSTS=[host]):
        landing = client.get(path, secure=True, HTTP_HOST=host)
        csrf = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', landing.content.decode()).group(1)
        response = client.post(path, {'csrfmiddlewaretoken':csrf}, secure=True, HTTP_HOST=host, HTTP_ORIGIN='https://'+host)
        html = response.content.decode()
        check(response.status_code == 200 and 'Service verification passed' in html, name+' real backend release passes')
        check('Holder edited this suggestion' in html and 'DigiLocker-associated QR detected' in html
              and 'DigiLocker branding detected' in html and 'Issuer not verified' in html, name+' selected signed states render')
        check('Synthetic Hidden Student' not in html and 'Science' not in html, name+' hidden fact values and labels absent')
        exported = client.get('/proof-download/'+secret['grant']+'/', secure=True, HTTP_HOST=host)
        check(exported.status_code == 200 and exported.json()['intakeStatus']['facts'][0]['lineage']=='EDITED', name+' session-bound export retains signed lineage')
        if public:
            check(client.get('/wallet/', secure=True, HTTP_HOST=host).status_code == 404, 'restricted profile has no holder route')
            check('id="verify-independent"' not in html, 'public profile preserves restricted independent-verifier policy')
        (OUT/(name+'.html')).write_text(html, encoding='utf8')
    (OUT/(name+'-checks.json')).write_text(json.dumps(checks, indent=2))

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--profile', choices=['private','receiver']);parser.add_argument('--reference',type=Path)
    args=parser.parse_args()
    if args.profile:
        profile(args.profile)
    else:
        import fitz
        auth=('p0-'+uuid.uuid4().hex[:12], 'fictional-'+uuid.uuid4().hex)
        call('POST','/api/auth/register',json={'username':auth[0],'password':auth[1],'role':'HOLDER'})
        document=fitz.open();page=document.new_page()
        page.insert_text((50,70),'SYNTHETIC TEST - no issuer authentication',fontsize=14)
        page.insert_text((50,110),'Name: Synthetic Hidden Student\nMath: 90\nScience: 80\nLate fee: INR 9300 unless cancellation applies.',fontsize=14)
        if args.reference:
            page.insert_image(fitz.Rect(40,250,550,365),filename=str(args.reference))
        else:
            import importlib.util
            spec=importlib.util.spec_from_file_location('fixtures',ROOT/'tools/make-intake-fixtures.py');fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
            import base64
            qr=fixtures.qr(json.dumps(['5005','1','Y',base64.b64encode(bytes(256)).decode()]))
            page.insert_image(fitz.Rect(40,240,180,380),stream=fixtures.png(qr))
            page.insert_image(fitz.Rect(310,270,550,370),filename=str(ROOT/'spring-boot-service/src/main/resources/indicators/digilocker-brand.png'))
        source=document.tobytes();document.close()
        start=time.perf_counter()
        d=call('POST','/api/wallet/documents',auth,files={'file':('p0-fictional.pdf',source,'application/pdf')},data={'displayName':'P0 fictional fixture','category':'Education'})
        cid=d['id'];deadline=time.monotonic()+300
        while time.monotonic()<deadline:
            report=call('GET','/api/wallet/intake/documents/'+cid,auth)
            if report['state'] not in ('QUEUED','RUNNING'):break
            time.sleep(1)
        elapsed=round((time.perf_counter()-start)*1000)
        (OUT/'private-intake-report.json').write_text(json.dumps(report))
        check(report['checks']['qr']=='PASSED' and report['checks']['branding']=='PASSED','actual PDF has independently positive QR and branding checks')
        check(report['checks']['imported']=='NOT_APPLICABLE' and report['checks']['issuer']=='UNVERIFIED','manual upload never gains import or issuer authority')
        fields=[{k:f[k] for k in ('path','label','type','value')} for f in report['fields']]
        math=next(f for f in fields if f['label']=='Math');math['value']='95'
        d=call('PUT','/api/wallet/documents/'+cid+'/claims',auth,json={'claims':fields})
        check(d['intake']['lineage']=='SUGGESTIONS_MODIFIED','server records holder edit')
        d=call('POST','/api/wallet/documents/'+cid+'/anchor',auth)
        chosen=next(f for f in d['claims'] if f['label']=='Math')
        grant=call('POST','/api/wallet/disclosures',auth,json={'credentialId':cid,'claimIds':[chosen['id']],
            'verifierLabel':'Fictional reviewer','purpose':'P0 status acceptance','expiresInMinutes':60,'oneTime':False,'includeDocumentStatus':True})
        token=grant['shareUrl'].rstrip('/').split('/')[-1]
        opened=call('POST','/api/public/disclosures/'+token+'/open');proof=opened['bundle'];status=proof['intakeStatus']
        check(opened['verification']['verified'] and status['facts'][0]['lineage']=='EDITED' and len(status['facts'])==1,'selected lineage is verified and scoped')
        for change in ('qr','lineage','strip'):
            forged=copy.deepcopy(proof)
            if change=='qr':forged['intakeStatus']['qr']='FAILED'
            elif change=='lineage':forged['intakeStatus']['facts'][0]['lineage']='UNCHANGED'
            else:del forged['intakeStatus']
            rejected=HTTP.post(API+'/api/public/verify-bundle',json=forged,timeout=60)
            check(rejected.status_code==400 or (rejected.ok and not rejected.json()['verified']),'tampered '+change+' fails verification')
        artifact=OUT/'proof.json';artifact.write_text(json.dumps(proof))
        pins=json.loads((ROOT/'.local-data/trusted-deployment.json').read_text(encoding='utf-8-sig'))
        result=subprocess.run(['node',str(ROOT/'spring-boot-service/scripts/verify-proof.cjs'),str(artifact),
            '--contract',pins['contract'],'--operator',pins['operator'],'--chain-id',str(pins['chainId']),'--rpc',RPC],capture_output=True)
        check(result.returncode==0,'independent pinned JavaScript verifier accepts new signed extension')
        (OUT/'checkpoint.json').write_text(json.dumps({'token':token,'grant':grant['id'],'auth':auth,'credentialId':cid}))
        for name in ('private','receiver'):
            subprocess.run([sys.executable,__file__,'--profile',name],check=True)
        (OUT/'results.json').write_text(json.dumps({'checks':checks,'intakeEndToEndMs':elapsed,'profiles':'fresh Django middleware/CSRF + real Spring HTTP; no tunnel'},indent=2))
