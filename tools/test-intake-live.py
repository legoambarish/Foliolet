"""Real isolated PostgreSQL/vault/HTTP/Ollama/Tesseract/watcher/EVM acceptance gate.

Only synthetic test documents and newly registered disposable accounts are used.
Secrets and bearer URLs stay in ignored local state, never in the result report.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone

import requests
import psycopg

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.local-data/intake-tests'
FIXTURES = OUT / 'fixtures'
API = os.environ.get('INTAKE_TEST_API', 'http://127.0.0.1:8088')
UI = os.environ.get('INTAKE_TEST_UI', 'http://127.0.0.1:8008')
DSN = os.environ.get('INTAKE_TEST_DSN', 'host=127.0.0.1 port=55438 dbname=wallet_intake_demo user=wallet')
RPC = os.environ.get('INTAKE_TEST_RPC', 'http://127.0.0.1:8548')
HTTP = requests.Session(); HTTP.trust_env = False
checks = []
for origin in (API, UI):
    assert origin.startswith('http://127.0.0.1:'), 'Use only the isolated numeric-loopback demo'


def check(condition, name):
    assert condition, name
    checks.append({'name': name, 'result': 'PASS'})
    print(datetime.now().strftime('%H:%M:%S'), 'PASS', name, flush=True)


def request(method, path, auth=None, expected=200, **kwargs):
    response = HTTP.request(method, API + path, auth=auth, timeout=(5, 60), **kwargs)
    # Real source rendering has its own bounded reader gate; wait without relaxing it.
    if method == 'GET' and path.startswith('/api/foli/'):
        for _ in range(30):
            if response.status_code != 429: break
            time.sleep(1)
            response = HTTP.request(method, API + path, auth=auth, timeout=(5, 60), **kwargs)
    assert response.status_code == expected, f'{method} private route returned {response.status_code}; expected {expected}'
    return response.json() if 'application/json' in response.headers.get('Content-Type', '') else response


def account():
    auth = ('intake-live-' + uuid.uuid4().hex[:12], 'isolated-password-' + uuid.uuid4().hex)
    request('POST', '/api/auth/register', json={'username': auth[0], 'password': auth[1], 'role': 'HOLDER'})
    return auth


def upload(auth, filename, previous=None):
    path = '/api/wallet/documents' + ('/' + previous + '/versions' if previous else '')
    return request('POST', path, auth, files={'file': (filename, (FIXTURES / filename).read_bytes(), 'application/pdf')},
                   data={'displayName': 'Synthetic ' + filename, 'category': 'Other'})['id']


def analysis(auth, credential):
    deadline, last, last_notice = time.monotonic() + 310, None, 0
    while time.monotonic() < deadline:
        result = request('GET', '/api/wallet/intake/documents/' + credential, auth)
        if result.get('state') not in ('QUEUED', 'RUNNING'):
            return result
        now = time.monotonic()
        if result.get('stage') != last or now-last_notice > 12:
            print(datetime.now().strftime('%H:%M:%S'), 'ACTIVE', result.get('stage'), flush=True)
            last, last_notice = result.get('stage'), now
        time.sleep(1)
    raise AssertionError('Analysis exceeded its five-minute server budget')


def claims(result):
    return [{k: field[k] for k in ('path', 'label', 'type', 'value')} for field in result['fields']]


def confirm(auth, credential, fields):
    return request('PUT', '/api/wallet/documents/' + credential + '/claims', auth, json={'claims': fields})


def independent(bundle, expected=True):
    artifact = OUT / 'synthetic-proof.json'
    artifact.write_text(json.dumps(bundle), encoding='utf-8')
    network = json.loads((ROOT / '.local-data/trusted-deployment.json').read_text(encoding='utf-8-sig'))
    result = subprocess.run(['node', str(ROOT / 'spring-boot-service/scripts/verify-proof.cjs'), str(artifact),
                             '--contract', network['contract'], '--operator', network['operator'], '--chain-id', str(network['chainId']),
                             '--rpc', RPC], capture_output=True, text=True)
    assert (result.returncode == 0) == expected, 'Independent pinned verifier result'


def share(auth, credential, claim_id, one_time=False):
    result = request('POST', '/api/wallet/disclosures', auth, json={'credentialId': credential, 'claimIds': [claim_id],
        'verifierLabel': 'Synthetic reviewer', 'purpose': 'Intake regression', 'expiresInMinutes': 5, 'oneTime': one_time})
    return result, '/api/public/disclosures/' + result['shareUrl'].rstrip('/').split('/')[-1] + '/open'


def foli(auth, **body):
    job = request('POST', '/api/foli/jobs', auth, expected=202, headers={'X-Foli-Client': 'private'}, json=body)
    deadline, notice = time.monotonic() + 300, 0
    while time.monotonic() < deadline:
        job = request('GET', '/api/foli/jobs/' + job['id'], auth)
        if job['state'] not in ('QUEUED', 'RUNNING'):
            assert job['state'] == 'COMPLETE', 'Existing Foli request did not complete: ' + job.get('code', '')
            return job['result']
        if time.monotonic() - notice > 12:
            print(datetime.now().strftime('%H:%M:%S'), 'ACTIVE Foli', job['stage'], flush=True)
            notice = time.monotonic()
        time.sleep(1)
    raise AssertionError('Existing Foli request exceeded its budget')


def formats_only():
    """A common two-column CSV is readable but must not be guessed into facts."""
    OUT.mkdir(parents=True, exist_ok=True)
    owner = account()
    content = b'Subject,Score\r\nMath,90\r\nScience,80\r\n'
    credential = request('POST', '/api/wallet/documents', owner,
        files={'file': ('synthetic-marks.csv', content, 'text/csv')},
        data={'displayName': 'Synthetic CSV fallback', 'category': 'Education'})['id']
    result = analysis(owner, credential)
    manifest = result['report']['manifest']
    check(manifest['format'] == 'csv' and manifest['complete'] and manifest['accountedPages'] == manifest['totalPages'],
          'CSV physical source is read completely with explicit coverage')
    check(result['state'] == 'NO_VERIFIABLE_FIELDS' and not result['fields']
          and request('GET', '/api/wallet/documents/' + credential + '/file', owner).content == content,
          'Ambiguous CSV layout yields no guessed facts and retains exact original')
    document = confirm(owner, credential, [{'path': 'education.math', 'label': 'Math', 'type': 'decimal', 'value': '90'}])
    check(document['intake']['lineage'] == 'NOT_ASSESSED' and document['intake']['issuer'] == 'NOT_VERIFIED',
          'CSV fallback permits holder-confirmed manual facts without AI or issuer assurance')
    (OUT / 'format-results.json').write_text(json.dumps({'checks': checks, 'count': len(checks), 'synthetic': True}, indent=2), encoding='utf8')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    owner, other = account(), account()
    (OUT / 'live-private-checkpoint.json').write_text(json.dumps({'auth': owner, 'other': other}), encoding='utf-8')
    health = request('GET', '/api/foli/health', owner)
    check(health['ollama']['status'] == 'READY' and health['ollama']['model'] == 'qwen3:4b-instruct', 'Existing local Qwen model is ready; no model downloaded')
    request('GET', '/api/wallet/intake/sessions', expected=401)
    check(True, 'Private session API requires holder authentication')
    folder = OUT / ('incoming-' + uuid.uuid4().hex)
    folder.mkdir()
    (folder / 'preexisting.txt').write_text('Pre-existing private file must not be imported')
    time.sleep(1)
    config = request('POST', '/api/wallet/intake/sessions', owner, json={'folder': str(folder)})
    config['apiUrl'] = API
    pair = OUT / 'synthetic-pair.json'; pair.write_text(json.dumps(config), encoding='utf-8')
    headers = {'Authorization': 'Bearer ' + config['token']}
    request('POST', '/api/intake-agent/heartbeat', headers={**headers, 'Origin': UI}, data={'folderHash': config['folderHash']}, expected=401)
    request('GET', '/api/wallet/documents', headers=headers, expected=401)
    request('POST', '/api/wallet/intake/sessions/' + config['sessionId'] + '/stop', other, expected=404)
    check(True, 'Capability rejects browser Origin, full-wallet access and cross-owner stop')
    log = (OUT / 'watcher-live.log').open('w', encoding='utf-8')
    child = subprocess.Popen([sys.executable, str(ROOT / 'tools/local-watcher/intake.py'), '--config', str(pair), '--app-pid', str(os.getpid())],
        cwd=ROOT, stdout=log, stderr=log, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            sessions = request('GET', '/api/wallet/intake/sessions', owner)
            if sessions[0]['connected']: break
            assert child.poll() is None, 'Native companion stopped unexpectedly'
            time.sleep(.5)
        check(sessions[0]['connected'], 'Real recursive companion heartbeat connects to armed session')
        incoming = folder / 'semester' / 'nested'; incoming.mkdir(parents=True)
        partial = incoming / 'marks.pdf.crdownload'
        content = (FIXTURES / 'both.pdf').read_bytes()
        partial.write_bytes(content[:500]); time.sleep(3)
        check(request('GET', '/api/wallet/intake/sessions', owner)[0]['imported'] == 0, 'Partial browser download and pre-existing files are ignored')
        partial.write_bytes(content); final = incoming / 'marks.pdf'; partial.rename(final)
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            sessions = request('GET', '/api/wallet/intake/sessions', owner)
            if sessions[0]['imported']: break
            time.sleep(.5)
        check(sessions[0]['imported'] == 1, 'Finished recursive rename imports one document automatically')
        credential = sessions[0]['documents'][0]['id']
        os.utime(final, None); time.sleep(3)
        check(request('GET', '/api/wallet/intake/sessions', owner)[0]['imported'] == 1, 'Repeated file events do not duplicate enrollment')
        original = request('GET', '/api/wallet/documents/' + credential + '/file', owner)
        check(original.content == content == final.read_bytes(), 'Download, observation-bound upload and decrypted vault bytes match exactly')
        request('GET', '/api/wallet/intake/documents/' + credential, other, expected=404)
        request('GET', '/api/wallet/documents/' + credential + '/file', other, expected=404)
        result = analysis(owner, credential)
        check(result['indicator'] == 'POSSIBLE_DIGILOCKER_FORMAT' and result['issuer'] == 'NOT_VERIFIED', 'Copied synthetic indicators remain possible and issuer-unverified')
        fields = claims(result)
        check(any(f['path'] == 'education.math' and f['value'] == '90' for f in fields), 'Live local Ollama proposes Math 90 with deterministic source validation')
        check(not any(f['path'] == 'education.cgpa' for f in fields), 'Unavailable CGPA is never fabricated')
        for field in result['fields']:
            citation = field['citation']
            assert citation['sourceHash'] == hashlib.sha256(content).hexdigest()
            source = request('GET', '/api/foli/source', owner, params={'documentId': citation['documentId'], 'hash': citation['sourceHash'], 'page': citation['page']})
            assert field['evidence'] in json.dumps(source)
        check(True, 'Every accepted field has an owner-authorized exact source quote, page and retained-byte hash')
        reordered = list(reversed(fields))
        document = confirm(owner, credential, reordered)
        check(document['intake']['lineage'] == 'SUGGESTIONS_UNMODIFIED', 'Reordered canonical facts confirm as AI suggestions unchanged')
        changed = copy.deepcopy(fields)
        next(f for f in changed if f['path'] == 'education.math')['value'] = '95'
        document = confirm(owner, credential, changed)
        check(document['intake']['lineage'] == 'SUGGESTIONS_MODIFIED' and document['intake']['changes']['edited'] == 1, 'Changing Math 90 to 95 is recorded server-side')
        attempted = HTTP.put(API + '/api/wallet/documents/' + credential + '/claims', auth=owner,
                             json={'claims': changed, 'unaltered': True, 'baseline': changed}, timeout=15)
        assert attempted.status_code in (200, 400), 'Unexpected response to client lineage flags'
        document = request('GET', '/api/wallet/documents/' + credential, owner)
        check(document['intake']['lineage'] == 'SUGGESTIONS_MODIFIED', 'Client-supplied unaltered flag and replacement baseline cannot erase edits')
        with_extra = fields + [{'path': 'extracted.holder_note', 'label': 'Holder note', 'type': 'string', 'value': 'Synthetic addition'}]
        check(confirm(owner, credential, with_extra)['intake']['changes']['added'] == 1, 'Adding a holder field changes lineage')
        check(confirm(owner, credential, fields[1:])['intake']['changes']['removed'] == 1, 'Removing an AI field changes lineage')
        document = confirm(owner, credential, fields)
        saved_baseline = document['intake']['fields']
        request('POST', '/api/wallet/intake/documents/' + credential + '/retry', owner)
        retried = analysis(owner, credential)
        check(retried['fields'] == saved_baseline, 'Explicit analysis retry preserves the immutable initial proposal')
        document = request('POST', '/api/wallet/documents/' + credential + '/anchor', owner)
        check(document['status'] == 'ACTIVE' and document['provenanceLevel'] == 'FIRST_SEEN_TRACKED', 'Existing explicit anchor retains the original first-seen assurance class')
        math = next(f for f in document['claims'] if f['path'] == 'education.math')
        grant, endpoint = share(owner, credential, math['id'])
        scanner = HTTP.get(API + endpoint, timeout=10)
        check(scanner.status_code in (401, 405), 'Passive GET cannot release or consume a proof')
        opened = request('POST', endpoint)
        check(opened['verification']['verified'] and len(opened['bundle']['claims']) == 1, 'Selective disclosure releases only the chosen committed fact')
        independent(opened['bundle'])
        forged = copy.deepcopy(opened['bundle']); forged['claims'][0]['leaf']['value'] = '95'
        independent(forged, False)
        check(True, 'Independent pinned verifier accepts real chain proof and rejects altered fact value')
        request('POST', '/api/wallet/disclosures/' + grant['id'] + '/revoke', owner)
        check(request('GET', '/api/public/grants/' + grant['id'] + '/status')['status'] == 'REVOKED', 'Existing share revocation remains effective')
        once, once_endpoint = share(owner, credential, math['id'], True)
        request('POST', once_endpoint)
        response = HTTP.post(API + once_endpoint, timeout=10)
        check(response.status_code in (409, 410), 'Existing one-time grant rejects a second release')
        expiry, expiry_endpoint = share(owner, credential, math['id'])
        with psycopg.connect(DSN) as db:
            db.execute("UPDATE disclosure_grants SET expires_at=now()-interval '1 minute' WHERE id=%s", (expiry['id'],))
        response = HTTP.post(API + expiry_endpoint, timeout=10)
        check(response.status_code in (409, 410), 'Existing expired grant rejects release')
        request('POST', '/api/wallet/intake/sessions/' + config['sessionId'] + '/stop', owner)
        request('POST', '/api/intake-agent/heartbeat', headers=headers, data={'folderHash': config['folderHash']}, expected=401)
        check(True, 'Stop watching revokes the companion capability')
    finally:
        if child.poll() is None: child.terminate()
        child.wait(timeout=10); log.close()
    manual = upload(owner, 'marks.txt')
    manual_result = analysis(owner, manual)
    check(manual_result['method'] == 'MANUAL_UPLOAD' and any(f['value'] == '90' for f in manual_result['fields']), 'Manual import works with watcher stopped')
    for filename, expected in [('logo-only.pdf', 'POSSIBLE_DIGILOCKER_FORMAT'), ('qr-only.pdf', 'POSSIBLE_DIGILOCKER_FORMAT'),
                               ('neither.pdf', 'NO_DIGILOCKER_INDICATOR'), ('unrelated-qr.pdf', 'NO_DIGILOCKER_INDICATOR'),
                               ('last-page.pdf', 'POSSIBLE_DIGILOCKER_FORMAT'), ('scanned.pdf', 'POSSIBLE_DIGILOCKER_FORMAT'),
                               ('hybrid.pdf', 'POSSIBLE_DIGILOCKER_FORMAT')]:
        # Independent disposable holders keep each scenario below production rate limits.
        detector_owner = account()
        cid = upload(detector_owner, filename); report = analysis(detector_owner, cid)
        check(report['indicator'] == expected and report['issuer'] == 'NOT_VERIFIED', 'Live PDFBox/Tesseract indicator outcome: ' + filename)
        if filename == 'scanned.pdf':
            check(report['report']['manifest']['ocrPages'] == 1 and any(f['path'] == 'education.math' and f['value'] == '90' for f in report['fields']), 'Scanned PDF supplies source-aligned Math 90 with OCR provenance')
        if filename == 'hybrid.pdf':
            check(any(p['status'] == 'MIXED_OCR' for p in report['report']['manifest']['pages']), 'Hybrid PDF retains native text, OCR text and uncertainty')
        if filename == 'neither.pdf':
            check(request('GET', '/api/wallet/documents/' + cid, detector_owner)['provenanceLevel'] == 'SELF_ENROLLED',
                  'Absent indicators preserve the existing self-enrolled assurance class')
    failure_owner = account()
    for filename, state in [('malformed.pdf', 'CORRUPT_SOURCE'), ('protected.pdf', 'PROTECTED_PDF'), ('unsupported.docx', 'UNSUPPORTED_FORMAT')]:
        cid = upload(failure_owner, filename); report = analysis(failure_owner, cid)
        check(report['state'] == state and request('GET', '/api/wallet/documents/' + cid + '/file', failure_owner).content == (FIXTURES / filename).read_bytes(), 'Failure retains exact original and manual fallback: ' + filename)
    version = upload(owner, 'marks.txt', credential)
    version_result = analysis(owner, version)
    check(request('GET', '/api/wallet/documents/' + version, owner)['version'] == 2 and version_result['lineage'] == 'NOT_ASSESSED'
          and all(f['citation']['sourceHash'] == hashlib.sha256((FIXTURES / 'marks.txt').read_bytes()).hexdigest() for f in version_result['fields']),
          'New version gets independent source-bound baseline and unassessed lineage')
    review_credential = upload(owner, 'neither.pdf')
    analysis(owner, review_credential)
    before = request('GET', '/api/wallet/documents/' + credential, owner)
    chain_before = HTTP.post(RPC, json={'jsonrpc': '2.0', 'id': 1, 'method': 'eth_blockNumber', 'params': []}, timeout=5).json()['result']
    refused = HTTP.post(API + '/api/foli/jobs', auth=owner, json={'mode': 'chat', 'question': 'Synthetic boundary control'}, timeout=10)
    check(refused.status_code == 403, 'Original Foli write-shaped requests still require the private-client boundary header')
    general = foli(owner, question='Explain briefly what a cryptographic hash is.', mode='chat')
    check(general['answerKind'] == 'GENERAL' and not general['citations'], 'Original general Foli chat works without fabricated document citations')
    answer = foli(owner, documentId='wallet:' + review_credential, question='What is the late fee and when does it apply?', mode='chat')
    check(answer['citations'] and any('9300' in c['quote'] for c in answer['citations']), 'Original document Foli chat retains exact source citations')
    review = foli(owner, documentId='wallet:' + review_credential, mode='review')
    check(review['answerKind'] == 'DOCUMENT_REVIEW' and review['manifest']['complete'] and review['findings']
          and any('unless' in c['quote'] or '9300' in c['quote'] for c in review['citations']), 'Original complete fine-print review retains fee and exception evidence')
    chain_after = HTTP.post(RPC, json={'jsonrpc': '2.0', 'id': 2, 'method': 'eth_blockNumber', 'params': []}, timeout=5).json()['result']
    check(before == request('GET', '/api/wallet/documents/' + credential, owner) and chain_before == chain_after,
          'Foli general chat, document chat and review leave wallet facts, lineage and chain unchanged')
    # Credentials are intentionally excluded from the durable evidence report.
    (OUT / 'ui-fixture-private.json').write_text(json.dumps({'auth': owner, 'document': manual, 'watcherDocument': credential}), encoding='utf-8')
    (OUT / 'live-results.json').write_text(json.dumps({'checks': checks, 'count': len(checks), 'synthetic': True, 'realDigiLockerTrial': 'NOT TESTED'}, indent=2), encoding='utf-8')
    print('PASS', len(checks), 'live checks; authentic issuer documents and NFC hardware NOT TESTED', flush=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--formats-only', action='store_true', help='Run the strict CSV/manual-fallback gate only')
    arguments = parser.parse_args()
    formats_only() if arguments.formats_only else main()
