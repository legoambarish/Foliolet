"""Disposable failure backend; never stops/reconfigures the user's Ollama server.

Tests real connection refusal, a missing OCR executable, process restart and HTTP
failure responses. Missing/oversized model metadata and bad proposals use an
explicit local test double, not a claimed test on real large model weights.
"""
import http.server
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime

import psycopg
from psycopg import sql
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.local-data/intake-tests'
PORT = int(os.environ.get('INTAKE_FAILURE_PORT', '8098'))
API = f'http://127.0.0.1:{PORT}'
HTTP = requests.Session(); HTTP.trust_env = False
checks = []
mode = 'missing'
model_calls = 0


def check(condition, name):
    assert condition, name
    checks.append({'name': name, 'result': 'PASS'})
    print(datetime.now().strftime('%H:%M:%S'), 'PASS', name, flush=True)


class LocalModelDouble(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def send(self, body):
        data = json.dumps(body).encode()
        try:
            self.send_response(200); self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError): pass
    def do_GET(self):
        if self.path == '/api/status': return self.send({'cloud': {'disabled': mode != 'cloud'}})
        if self.path == '/api/tags':
            models = [] if mode == 'missing' else [{'name': 'qwen3:4b-instruct', 'size': 7_000_000_000 if mode == 'oversized' else 2_497_293_803, 'digest': 'synthetic'}]
            return self.send({'models': models})
        self.send({})
    def do_POST(self):
        global model_calls
        self.rfile.read(int(self.headers.get('Content-Length', 0)))
        model_calls += 1
        if mode == 'timeout': time.sleep(6)
        proposal = {'pairs': [{'labelCell': 'FORGED' if mode == 'forged' else 'P1_native_R1_C0', 'valueCell': 'P1_native_R1_C1', 'value':'FORGED'}]}
        self.send({'model': 'qwen3:4b-instruct', 'created_at': '2026-10-16T00:00:00Z', 'message': {'role': 'assistant', 'content': json.dumps(proposal)},
                   'done': True, 'done_reason': 'stop', 'prompt_eval_count': 10, 'eval_count': 10})


def call(method, path, auth=None, **kw):
    r = HTTP.request(method, API + path, auth=auth, timeout=(3, 15), **kw)
    assert r.status_code == 200, 'Failure-backend route returned ' + str(r.status_code)
    return r.json() if 'application/json' in r.headers.get('Content-Type', '') else r


def upload(auth, name='marks.txt'):
    return call('POST', '/api/wallet/documents', auth, files={'file': (name, (OUT / 'fixtures' / name).read_bytes())}, data={'displayName': 'Synthetic failure', 'category': 'Other'})['id']


def done(auth, identifier):
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        r = call('GET', '/api/wallet/intake/documents/' + identifier, auth)
        if r.get('state') not in ('QUEUED', 'RUNNING'): return r
        time.sleep(.25)
    raise AssertionError('Failure job exceeded bounded test deadline')


def start_backend(env, logfile):
    child = subprocess.Popen(['java', '-jar', os.environ.get('FOLIOLET_TEST_JAR', str(ROOT / 'spring-boot-service/target/dms-0.0.1-SNAPSHOT.jar'))], cwd=ROOT / 'spring-boot-service', env=env,
                             stdout=logfile, stderr=logfile, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        assert child.poll() is None, 'Disposable failure backend exited during startup; inspect its local log'
        try:
            if HTTP.get(API + '/api/public/network', timeout=1).status_code == 200: return child
        except requests.RequestException: pass
        time.sleep(1)
    child.terminate(); child.wait(timeout=10)
    raise AssertionError('Disposable failure backend did not start')


def main():
    global mode
    OUT.mkdir(parents=True, exist_ok=True)
    for port in (PORT, 11439):
        with socket.socket() as probe: probe.bind(('127.0.0.1', port))
    import fitz
    with fitz.open() as pdf:
        page=pdf.new_page()
        page.insert_text((40,60),'FICTIONAL LOCAL LINKER FAILURE TEST')
        page.insert_text((40,120),'Award Code')
        page.insert_text((240,120),'NV001')
        pdf.save(OUT/'fixtures/linker.pdf')
    suffix = uuid.uuid4().hex[:10]
    database = 'intake_fault_' + suffix
    state = OUT / ('failure-runtime-' + suffix); state.mkdir()
    with psycopg.connect(os.environ.get('INTAKE_TEST_ADMIN_DSN', 'host=127.0.0.1 port=55438 dbname=postgres user=wallet'), autocommit=True) as db:
        db.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
    env = os.environ.copy()
    env.update({'SERVER_ADDRESS': '127.0.0.1', 'SERVER_PORT': str(PORT), 'SPRING_DATASOURCE_URL': os.environ.get('INTAKE_TEST_JDBC_PREFIX', 'jdbc:postgresql://127.0.0.1:55438/') + database,
                'SPRING_DATASOURCE_USERNAME': os.environ.get('INTAKE_TEST_DB_USER', 'wallet'), 'SPRING_DATASOURCE_PASSWORD': os.environ.get('INTAKE_TEST_DB_PASSWORD', ''), 'SPRING_JPA_HIBERNATE_DDL_AUTO': 'update', 'SPRING_JPA_OPEN_IN_VIEW': 'false',
                'BLOCKCHAIN_RPC_URL': 'http://127.0.0.1:8548', 'BLOCKCHAIN_EXPECTED_CHAIN_ID': '1337',
                'BLOCKCHAIN_PRIVATE_KEY': (ROOT / '.local-data/development-relay.key').read_text().strip(), 'WALLET_DATA_DIR': str(state),
                'WALLET_SHARE_BASE_URL': 'http://127.0.0.1:8008', 'DMS_STORAGE_LOCATION': str(state / 'legacy/files'), 'DMS_BACKUP_LOCATION': str(state / 'legacy/backups'),
                'OPENROUTER_API_KEY': '', 'OPENROUTER_MODEL': 'disabled', 'FOLI_OLLAMA_URL': 'http://127.0.0.1:11439', 'FOLI_MODEL': 'qwen3:4b-instruct',
                'FOLI_TESSERACT': str(state / 'missing-tesseract.exe'),
                'FOLI_LAYOUT_PYTHON': str(state / 'missing-python'), 'FOLI_LAYOUT_SCRIPT': '',
                'FOLI_TEMP_DIR': str(state / 'tmp'), 'FOLI_MODEL_TIMEOUT_SECONDS': '3',
                'FOLI_OCR_TIMEOUT_SECONDS': '2', 'FOLI_EXTRACTION_TIMEOUT_SECONDS': '15', 'LOGGING_LEVEL_ORG_APACHE_PDFBOX': 'OFF', 'LOGGING_LEVEL_ORG_SPRINGFRAMEWORK_AI': 'OFF',
                'SERVER_TOMCAT_ACCESSLOG_ENABLED': 'false', 'SPRING_SERVLET_MULTIPART_MAX_FILE_SIZE': '20MB', 'SPRING_SERVLET_MULTIPART_MAX_REQUEST_SIZE': '21MB'})
    log = (state / 'backend.log').open('w', encoding='utf-8')
    child = start_backend(env, log); server = None
    try:
        def account():
            auth = ('failure-' + uuid.uuid4().hex[:12], 'isolated-' + uuid.uuid4().hex)
            call('POST', '/api/auth/register', json={'username': auth[0], 'password': auth[1], 'role': 'HOLDER'}); return auth
        auth = account()
        identifier = upload(auth); result = done(auth, identifier)
        check(result['state'] == 'READY' and any(f['value']=='90' for f in result['fields']), 'Structured source facts survive a real refused local model connection')
        check(call('GET', '/api/wallet/documents/' + identifier + '/file', auth).content == (OUT / 'fixtures/marks.txt').read_bytes(), 'Model outage preserves exact encrypted original')
        call('PUT', '/api/wallet/documents/' + identifier + '/claims', auth, json={'claims': [{'path': 'education.math', 'label': 'Math', 'type': 'decimal', 'value': '90'}]})
        check(call('GET', '/api/wallet/intake/documents/' + identifier, auth)['lineage'] == 'SUGGESTIONS_MODIFIED', 'Holder confirmation remains available during model outage with server-side removal tracking')
        scan = upload(auth, 'scanned.pdf'); unreadable = done(auth, scan)
        check(unreadable['indicator'] == 'POSSIBLE_DIGILOCKER_FORMAT' and unreadable['report']['manifest']['readablePages'] == 0
              and not unreadable['fields'] and unreadable['report']['manifest']['warnings'], 'Missing OCR is explicit; independent QR can remain possible without invented facts')
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 11439), LocalModelDouble)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        for failure, code in [('missing', 'MODEL_MISSING'), ('oversized', 'MODEL_SIZE_LIMIT'), ('cloud', 'CLOUD_NOT_DISABLED')]:
            mode = failure; before = model_calls
            r = done(account_auth := account(), upload(account_auth,'linker.pdf'))
            check(r['report']['modelCode'] == code and not r['fields'] and model_calls == before, 'Local model preflight rejects ' + failure + ' without inference')
        mode = 'forged'; auth = account(); identifier = upload(auth,'linker.pdf'); forged = done(auth, identifier)
        check(forged['state'] == 'NO_VERIFIABLE_FIELDS' and forged['report']['discarded'] == 1 and not forged['fields'], 'Forged model cell references cannot invent a field or supply a value')
        mode = 'timeout'; auth = account(); identifier = upload(auth,'linker.pdf'); before = time.monotonic(); timed = done(auth, identifier)
        check(timed['state'] == 'TIMED_OUT' and time.monotonic()-before < 20 and not timed['fields'], 'Delayed local inference times out without a baseline or lost upload')
        # Interrupt a real in-flight job and restart the same disposable backend/data.
        mode = 'timeout'; auth = account(); interrupted = upload(auth,'linker.pdf')
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if 'Checking unassociated source cells' in call('GET', '/api/wallet/intake/documents/' + interrupted, auth).get('stage', ''): break
            time.sleep(.1)
        child.terminate(); child.wait(timeout=10)
        child = start_backend(env, log)
        resumed = call('GET', '/api/wallet/intake/documents/' + interrupted, auth)
        check(resumed['state'] == 'INTERRUPTED' and call('GET', '/api/wallet/documents/' + interrupted + '/file', auth).content == (OUT / 'fixtures/linker.pdf').read_bytes(), 'Real backend restart marks an interrupted job and retains its original')
        mode = 'valid'; call('POST', '/api/wallet/intake/documents/' + interrupted + '/retry', auth)
        check(done(auth, interrupted)['fields'][0]['value'] == 'NV001', 'Owner retry after restart can create a source-bound proposal; model-supplied values are ignored')
        too_big = HTTP.post(API + '/api/wallet/documents', auth=auth, files={'file': ('oversized.txt', b'x' * (20*1024*1024+1))}, data={'displayName': 'Synthetic oversized', 'category': 'Other'}, timeout=20)
        check(too_big.status_code in (400, 413), 'Oversized upload is refused before enrollment')
    finally:
        if child.poll() is None: child.terminate(); child.wait(timeout=10)
        if server: server.shutdown(); server.server_close()
        log.close()
    (OUT / 'failure-results.json').write_text(json.dumps({'checks': checks, 'count': len(checks), 'modelMetadataCases': 'local HTTP test double; no oversized weights downloaded',
        'sharedOllama': 'untouched', 'retainedDisposableDatabase': database}, indent=2), encoding='utf-8')
    print('PASS', len(checks), 'failure checks; shared Ollama was untouched', flush=True)


if __name__ == '__main__': main()
