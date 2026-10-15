"""Check an intentionally stopped/restored local runtime. Never stops a service itself."""
import argparse
import json
from pathlib import Path
import runpy
import time

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'.local-data/foli'
qa=runpy.run_path(str(ROOT/'tools/test-foli-qa.py'))
parser=argparse.ArgumentParser(); parser.add_argument('--offline',action='store_true'); args=parser.parse_args()
auth=json.loads((OUT/'ui-fixture.json').read_text())['auth']
health=qa['call']('GET','/health',auth); health.raise_for_status(); status=health.json()['ollama']['status']
assert status==('OFFLINE' if args.offline else 'READY'),status
outcome,seconds=qa['job']({'mode':'chat','question':'Briefly explain careful reading.','history':[]},auth)
if args.offline:
    assert outcome['state']=='ERROR' and outcome['code']=='OFFLINE',outcome
    assert outcome['result'] is None
else:
    assert outcome['state']=='COMPLETE' and outcome['result']['answerKind']=='GENERAL'
    assert outcome['result']['answer']
path=OUT/'phase-5-outage.json'
report=json.loads(path.read_text()) if path.exists() else {}
report['offline' if args.offline else 'restored']={'status':status,'jobState':outcome['state'],'seconds':seconds,'time':time.strftime('%Y-%m-%dT%H:%M:%S%z')}
path.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PASS: actual runtime',status,'job',outcome['state'],seconds,'s')
