"""Measure actual HTTP first-useful/complete/reused jobs on fictional text only."""
import json
import os
from pathlib import Path
import time
import uuid
import requests

ROOT=Path(__file__).resolve().parents[1]
API=os.environ.get('INTAKE_TEST_API','http://127.0.0.1:8089')
assert API.startswith('http://127.0.0.1:')
http=requests.Session();http.trust_env=False
auth=('p0-jobs-'+uuid.uuid4().hex[:10],'fictional-'+uuid.uuid4().hex)
r=http.post(API+'/api/auth/register',json={'username':auth[0],'password':auth[1],'role':'HOLDER'});r.raise_for_status()
def call(method,path,**kw):
    r=http.request(method,API+path,auth=auth,timeout=60,**kw);r.raise_for_status();return r.json()
d=call('POST','/api/wallet/documents',files={'file':('fictional.txt',b'Name: Synthetic Person\nFee: INR 9300\nThe fee applies after 90 days unless timely cancellation applies.\nCancellation requires written notice within 7 days.','text/plain')},data={'displayName':'Fictional jobs benchmark','category':'Other'})
deadline=time.monotonic()+180
while time.monotonic()<deadline:
    intake=call('GET','/api/wallet/intake/documents/'+d['id'])
    if intake['state'] not in ('QUEUED','RUNNING'):break
    time.sleep(1)
records=[]
requests_to_measure=[('general',{'mode':'chat','question':'Explain selective disclosure in two sentences.'}),
    ('document',{'mode':'chat','question':'What is the fee and its exception?','documentId':'wallet:'+d['id']}),
    ('review',{'mode':'review','documentId':'wallet:'+d['id']})]
for kind,body in requests_to_measure:
    original=None
    for run in range(3):
        start=time.perf_counter();first=None
        job=call('POST','/api/foli/jobs',headers={'X-Foli-Client':'private'},json=body)
        while job['state'] in ('QUEUED','RUNNING'):
            if job.get('preview') and first is None:first=round((time.perf_counter()-start)*1000)
            assert time.perf_counter()-start<310,'Job exceeded application budget'
            time.sleep(.15);job=call('GET','/api/foli/jobs/'+job['id'])
        elapsed=round((time.perf_counter()-start)*1000)
        assert job['state']=='COMPLETE',job.get('code')
        if original is None:original=job['id']
        result=job['result']
        row={'kind':kind,'run':run,'totalMs':elapsed,'firstUsefulMs':first if first is not None else elapsed,
             'reused':run>0 and original==job['id'],'citations':len(result.get('citations',[])),
             'performance':result.get('performance',{}),'answerKind':result.get('answerKind')}
        assert run==0 or row['reused']
        records.append(row);print(json.dumps(row),flush=True)
        (ROOT/'.local-data/p0/job-metrics.json').write_text(json.dumps(records,indent=2))
print('Actual application jobs complete; reported model time on reused jobs describes cached original computation.')
