"""Scoped audit regressions over real local HTTP, PostgreSQL and Django sessions."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
import psycopg
import requests

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('workflow', ROOT / 'tools/test-live-workflow.py')
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
check, call = w.check, w.call
sys.path.insert(0, str(ROOT / 'django-service'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hermes.settings')
import django
django.setup()
from django.contrib.sessions.models import Session


def main():
    pins = json.loads((ROOT / '.local-data/trusted-deployment.json').read_text())
    name = 'race_' + uuid.uuid4().hex[:10]
    auth = (name, 'local-demo-password-123')
    def register(_):
        return requests.post(w.BASE+'/api/auth/register', json={'username': name, 'password': auth[1], 'role': 'HOLDER'}, timeout=30).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted(pool.map(register, range(2)))
    check(results == [200, 409], 'concurrent real registration yields one success and one controlled conflict')
    with psycopg.connect(w.DB) as db:
        check(db.execute('SELECT count(*) FROM users WHERE username=%s', (name,)).fetchone()[0] == 1,
              'PostgreSQL retains exactly one account for the concurrent username')
        try:
            db.execute('INSERT INTO users(username,password,role) VALUES (%s,%s,%s)', (name, 'fixture', 'HOLDER'))
        except psycopg.errors.UniqueViolation:
            db.rollback()
            check(True, 'direct SQL duplicate rejected by database constraint')
        else:
            db.rollback()
            raise AssertionError('Database accepted duplicate username')

    ui = requests.Session()
    origin = 'http://localhost:8000'
    def post(path, data, files=None):
        landing = ui.get(origin+path, timeout=30)
        csrf = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', landing.text).group(1)
        fields = list(data) if isinstance(data, list) else list(data.items())
        return ui.post(origin+path, data=fields+[('csrfmiddlewaretoken', csrf)], files=files,
                       headers={'Origin': origin}, timeout=90)
    check(post('/login/', {'username':name, 'password':auth[1]}).status_code == 200, 'Django login works')
    source = b'Name: Hidden Audit Student\nCGPA: 9.17\nInstitution: Hidden Audit College\nCourse: Computing\nDate of birth: 2004-01-02\n'
    review = post('/wallet/enroll/', {'display_name':'Audit marksheet', 'category':'Education'},
                  {'file': ('marksheet.txt', source, 'text/plain')})
    check(review.status_code == 200 and 'Hidden Audit Student' in review.text, 'encrypted-original draft suggestions render after upload')
    check('Hidden Audit Student' in ui.get(review.url, timeout=30).text, 'draft refresh retrieves transient suggestions')
    decoded = Session.objects.get(session_key=ui.cookies['sessionid']).get_decoded()
    check('claim_suggestions' not in decoded and 'Hidden Audit Student' not in json.dumps(decoded),
          'actual signed Django session contains no extracted suggestions')
    credential = review.url.rstrip('/').split('/')[-1]
    draft = call('GET', '/api/wallet/documents/'+credential, auth)
    fields = [('confirm', 'yes')]
    for c in draft['suggestions']:
        fields += [('claim_'+k, c[k]) for k in ('path','label','type','value')]
    confirmed = post('/wallet/'+credential+'/', fields)
    check(confirmed.status_code == 200 and 'Platform-derived threshold' in confirmed.text, 'normal marksheet confirmation displays recognized derived threshold')
    check('suggestions' not in call('GET', '/api/wallet/documents/'+credential, auth), 'confirmed draft stops returning extraction suggestions')
    # Action endpoint is POST-only; use the CSRF token on its holder detail form.
    csrf = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', confirmed.text).group(1)
    anchored = ui.post(origin+'/wallet/'+credential+'/anchor/', data={'csrfmiddlewaretoken':csrf}, headers={'Origin':origin}, timeout=90)
    check(anchored.status_code == 200 and 'ACTIVE' in anchored.text, 'Django holder flow anchors real marksheet')
    d = call('GET', '/api/wallet/documents/'+credential, auth)
    share = w.share(auth, d)
    selective = call('POST', w.token_path(share))['bundle']
    for label, mutate in (
        ('unknown unsigned field', lambda b: b.update(unsignedExtra='not authenticated')),
        ('string boolean', lambda b: b['presentation'].update(oneTime='false')),
        ('boolean instead of claim string', lambda b: b['claims'][0]['leaf'].update(value=True)),
        ('missing flag', lambda b: b['presentation'].pop('oneTime')),
    ):
        malformed = copy.deepcopy(selective)
        mutate(malformed)
        call('POST', '/api/public/verify-bundle', expected=400, json=malformed)
        check(True, 'Java public verifier rejects '+label)
    all_share = call('POST','/api/wallet/disclosures',auth,json={'credentialId':credential,'claimIds':[c['id'] for c in d['claims']],
        'verifierLabel':'Fixture audit','purpose':'Check salt omission','expiresInMinutes':30,'oneTime':False})
    all_bundle = call('POST',w.token_path(all_share))['bundle']
    raw = json.dumps(selective)
    hidden = [c['leaf'] for c in all_bundle['claims'] if c['leaf']['path'] != 'education.cgpa_at_least_8_5']
    check(all(l['salt'] not in raw and l['value'] not in raw for l in hidden), 'selective bundle omits every hidden fixture value and salt')
    path = ROOT / '.local-data/security-demo-proof.json'
    path.write_text(json.dumps(selective))
    command = ['node', str(ROOT/'spring-boot-service/scripts/verify-proof.cjs'), str(path)]
    trusted = ['--contract',pins['contract'],'--operator',pins['operator'],'--chain-id',str(pins['chainId'])]
    good = subprocess.run(command+trusted,capture_output=True,text=True)
    check(good.returncode == 0, 'separate Node accepts genuine live proof with local pins')
    for flags in ([],trusted[:2],trusted[:4],trusted[:-1]+['invalid']):
        check(subprocess.run(command+flags,capture_output=True,text=True).returncode != 0, 'Node fails closed with missing or malformed required pins')
    changed = copy.deepcopy(selective)
    changed['claims'][0]['leaf']['value'] = 'false'
    path.write_text(json.dumps(changed))
    check(subprocess.run(command+trusted,capture_output=True,text=True).returncode != 0, 'Node rejects a tampered live proof')
    path.write_text(json.dumps(selective))

    custom = w.upload(auth, b'Custom fixture')
    custom = call('PUT', '/api/wallet/documents/'+custom['id']+'/claims', auth, json={'claims':[
        {'path':'custom.eligibility','label':'CGPA at least 8.5','type':'boolean','value':'true'}]})
    custom = call('POST','/api/wallet/documents/'+custom['id']+'/anchor',auth)
    cs = call('POST','/api/wallet/disclosures',auth,json={'credentialId':custom['id'],'claimIds':[custom['claims'][0]['id']],
        'verifierLabel':'Fixture audit','purpose':'Custom label distinction','expiresInMinutes':30,'oneTime':False})
    custom_page = post('/verify/'+cs['shareUrl'].rstrip('/').split('/')[-1]+'/',{})
    check(custom_page.status_code == 200 and 'Holder-authored statement' in custom_page.text
          and 'Custom label: CGPA at least 8.5' in custom_page.text and 'custom.eligibility' in custom_page.text
          and 'Platform-derived threshold' not in custom_page.text, 'real custom threshold label cannot acquire derived presentation')
    check(all('claim_suggestions' not in s.get_decoded() for s in Session.objects.all()), 'retained session rows contain no legacy suggestion copies after migration')
    (ROOT/'.local-data/security-demo-session.json').write_text(json.dumps({'username':name,'password':auth[1],'documentId':credential,'share':share,'customShare':cs,'network':pins}))
    (ROOT/'.local-data/live-security-results.json').write_text(json.dumps({'count':len(w.checks),'checks':w.checks},indent=2))
    print('Completed',len(w.checks),'live security checks',flush=True)


if __name__ == '__main__':
    main()
