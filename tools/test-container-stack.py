"""Disposable real-stack acceptance test. Requires Python 3 and a running Docker.

Uses a unique Compose project, synthetic documents, alternate free ports and its
own volumes. Never starts/stops the normal Foliolet project or reads user files.
"""
import argparse
from datetime import datetime, timezone
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, HTTPCookieProcessor, ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]


def log(message):
    print(datetime.now(timezone.utc).isoformat(timespec='seconds') + ' ' + message, flush=True)


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def wait_for(name, probe, seconds=120):
    deadline, last = time.monotonic() + seconds, 0
    while True:
        try:
            result = probe()
            if result:
                return result
        except (HTTPError, URLError, OSError):
            pass
        now = time.monotonic()
        if now > deadline:
            raise TimeoutError(name + ' timed out')
        if now - last > 10:
            log('[wait] ' + name); last = now
        time.sleep(1)


class Client:
    def __init__(self, origin):
        self.origin = origin
        self.cookies = http.cookiejar.CookieJar()
        self.http = build_opener(ProxyHandler({}), HTTPCookieProcessor(self.cookies))

    def request(self, path, form=None, payload=None):
        data, headers = None, {}
        if form is not None or payload is not None:
            csrf = next(c.value for c in self.cookies if c.name == 'csrftoken')
            headers = {'X-CSRFToken': csrf, 'Referer': self.origin + path}
            if payload is not None:
                data = json.dumps(payload).encode(); headers['Content-Type'] = 'application/json'
            else:
                data = urlencode(form).encode(); headers['Content-Type'] = 'application/x-www-form-urlencoded'
        with self.http.open(Request(self.origin + path, data=data, headers=headers), timeout=30) as response:
            body = response.read()
            return json.loads(body) if 'application/json' in response.headers.get('Content-Type', '') else body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wait-timeout', type=int, default=1800)
    args = parser.parse_args()
    project = 'foliolet-smoke-' + secrets.token_hex(6)
    evidence = ROOT / '.local-data' / project
    incoming = evidence / 'incoming'; incoming.mkdir(parents=True)
    env = dict(os.environ)
    ports = {free_port(), free_port()}
    while len(ports) < 2: ports.add(free_port())
    ui, rpc = ports
    env.update(FOLIOLET_INTAKE_DIR=str(incoming), FOLIOLET_HTTP_PORT=str(ui),
               FOLIOLET_RPC_PORT=str(rpc), FOLIOLET_SHARE_MODE='local')
    command = ['docker', 'compose', '-f', str(ROOT / 'compose.yaml'), '-p', project]
    started, success = False, False

    def compose(*arguments, capture=False, timeout=None):
        return subprocess.run(command + list(arguments), cwd=ROOT, env=env, check=True,
                              capture_output=capture, text=True, timeout=timeout)

    def identity():
        code = ("import hashlib,json,pathlib,urllib.request; r=pathlib.Path('/app/.local-data');"
                "print(json.dumps({'keys':{n:hashlib.sha256((r/n).read_bytes()).hexdigest() "
                "for n in ['development-relay.key','django.key','trusted-deployment.json']},"
                "'models':json.load(urllib.request.urlopen('http://127.0.0.1:11434/api/tags'))['models']}))")
        result = json.loads(compose('exec', '-T', 'app', 'python', '-c', code, capture=True, timeout=30).stdout)
        return {'keys': result['keys'], 'models': sorted((m['name'], m['digest']) for m in result['models'])}

    try:
        log('[check] Docker engine (no existing Foliolet processes will be changed)')
        subprocess.run(['docker', 'info', '--format', '{{.ServerVersion}}'], check=True, timeout=30)
        # Refuse even an accidental collision before any project mutation.
        if compose('ps', '-a', '-q', capture=True, timeout=30).stdout.strip():
            raise RuntimeError('Synthetic project name already exists; rerun to choose a new one')
        for resource in ('volume', 'network'):
            existing = subprocess.run(['docker', resource, 'ls', '-q', '--filter',
                'label=com.docker.compose.project=' + project], check=True, capture_output=True, text=True, timeout=30)
            if existing.stdout.strip():
                raise RuntimeError('Synthetic project resources already exist; rerun to choose a new name')
        old = b'Synthetic old document. Name: Container Holder.\n'
        (incoming / 'old.txt').write_bytes(old)
        os.utime(incoming / 'old.txt', (1700000000, 1700000000))
        started = True
        log('[start] Build and wait for the complete stack, including the real Ollama model')
        compose('up', '--build', '-d', '--wait', '--wait-timeout', str(args.wait_timeout), timeout=args.wait_timeout + 1800)
        client = Client('http://127.0.0.1:' + str(ui))
        client.request('/register/')
        password = secrets.token_urlsafe(24)
        client.request('/register/', form={'username':project, 'password':password, 'confirm_password':password})
        client.request('/login/', form={'username':project, 'password':password})
        html = client.request('/wallet/enroll/')
        assert b'data-managed="yes"' in html, 'Container UI or login failed'
        health = client.request('/ask-foli/api/health/')
        assert health['ollama']['status'] == 'READY' and health['ollama']['cloudDisabled'], health
        before = identity()
        rpc_http = build_opener(ProxyHandler({}))
        with rpc_http.open(Request('http://127.0.0.1:' + str(rpc),
                data=b'{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}',
                headers={'Content-Type':'application/json'}), timeout=10) as response:
            assert json.load(response)['result'] == '0x539'
        pairing = client.request('/intake/pair/', form={'folder':'/app/imports/foliolet', 'consent':'yes'})
        assert pairing['managed'] and 'token' not in pairing

        def session():
            return next((s for s in client.request('/intake/sessions/')['sessions'] if s['active']), {})

        wait_for('managed watcher heartbeat', lambda: session().get('connected'))
        # A first heartbeat can precede companion startup. Wait for its ready log
        # before testing a download; old pre-pairing documents remain click-importable.
        ready = ("import pathlib,sys; p=pathlib.Path('/app/.local-data/managed-intake/state');"
                 "sys.exit(0 if any(b'Watching while Foliolet' in f.read_bytes() for f in p.glob('*/companion.log')) else 1)")
        def watcher_started():
            try:
                compose('exec', '-T', 'app', 'python', '-c', ready, capture=True, timeout=15)
                return True
            except subprocess.CalledProcessError:
                return False
        wait_for('companion startup', watcher_started)

        def import_row(name, expected):
            rows = client.request('/intake/files/')['files']
            row = next(r for r in rows if r['name'] == name)
            result = client.request('/intake/files/import/', form={'selection':row['selection']})
            assert client.request(result['url'] + 'file/') == expected, 'Wrong original bytes'
            return result['id']

        old_id = import_row('old.txt', old)
        original_count = session()['imported']
        fresh = b'Synthetic new document. Institution: Container Test.\n'
        (incoming / 'fresh.txt').write_bytes(fresh)
        wait_for('automatic new-file import', lambda: session()['imported'] > original_count)
        rows = client.request('/intake/files/')['files']
        assert [r['name'] for r in rows] == ['fresh.txt', 'old.txt'], 'Incorrect live file ordering'
        fresh_id = import_row('fresh.txt', fresh)
        assert fresh_id != old_id
        assert session()['imported'] == original_count + 1, 'Click import duplicated the automatic import'
        log('[pass] UI, EVM, local model, consent, polling, newest-first list and exact-byte deduplication')

        # Exercise real inference through Django -> Spring AI -> Ollama.
        job = client.request('/ask-foli/api/jobs/', payload={'mode':'chat', 'question':'Reply with a short greeting.'})
        def completed():
            value = client.request('/ask-foli/api/jobs/' + job['id'] + '/')
            if value['state'] in ('ERROR', 'CANCELLED'):
                raise RuntimeError('Real model inference failed: ' + str(value.get('code')))
            return value if value['state'] == 'COMPLETE' else None
        wait_for('real local model inference', completed, seconds=240)
        log('[pass] Real Spring AI inference completed')

        # Down/up proves namespace recreation, persisted DB/chain/keys, model cache,
        # and automatic watcher resumption. No model is pulled a second time.
        compose('down', timeout=120)
        compose('up', '-d', '--wait', '--wait-timeout', str(args.wait_timeout), timeout=args.wait_timeout + 60)
        assert identity() == before, 'Persistent identity or model cache changed'
        assert client.request('/wallet/' + old_id + '/file/') == old
        wait_for('resumed watcher', lambda: session().get('connected'))
        count = session()['imported']
        (incoming / 'after-restart.csv').write_bytes(b'name,score\nSynthetic Holder,95\n')
        wait_for('automatic import after restart', lambda: session()['imported'] == count + 1)
        assert client.request('/intake/files/')['files'][0]['name'] == 'after-restart.csv'
        logs = compose('logs', '--no-color', 'app', capture=True, timeout=30).stdout
        assert 'Cached model ready; no download needed.' in logs
        success = True
        (evidence / 'result.json').write_text(json.dumps({'result':'PASS','project':project,
            'checks':['build','readiness','private-ui','evm','model-inference','managed-pairing','folder-polling',
                      'exact-original-bytes','newest-first','deduplication','restart-persistence','cached-model','watcher-resume']}, indent=2))
        log('[pass] Restart preserves account, originals, keys, trust pins, model cache and watcher pairing')
    finally:
        if not success:
            (evidence / 'result.json').write_text(json.dumps({'result':'FAILED','project':project}, indent=2))
        if started:
            try:
                logs = compose('logs', '--no-color', capture=True, timeout=30)
                (evidence / 'compose.log').write_text(logs.stdout + logs.stderr, encoding='utf-8')
            finally:
                # Only this freshly allocated, collision-checked synthetic project.
                # The user's default project and volumes are never selected.
                compose('down', '--volumes', '--remove-orphans', timeout=120)
        log(('[PASS] ' if success else '[FAILED] ') + 'Evidence: ' + str(evidence))


if __name__ == '__main__':
    main()
