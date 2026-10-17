"""Supervise the private loopback stack inside the application container."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, build_opener, ProxyHandler
from model import prepare

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.local-data'
HTTP = build_opener(ProxyHandler({}))


def environment(source, state=STATE, password_file=Path('/run/foliolet/postgres-password')):
    env = dict(source)
    http_port, rpc_port = int(env.get('FOLIOLET_HTTP_PORT', '8008')), int(env.get('FOLIOLET_RPC_PORT', '8548'))
    if not all(1024 <= port <= 65535 for port in (http_port, rpc_port)) or http_port == rpc_port:
        raise ValueError('Choose different valid host UI/RPC ports')
    env.update({
        'SPRING_DATASOURCE_URL': 'jdbc:postgresql://postgres:5432/foliolet',
        'SPRING_DATASOURCE_USERNAME': 'wallet', 'SPRING_DATASOURCE_PASSWORD': password_file.read_text().strip(),
        'SPRING_JPA_HIBERNATE_DDL_AUTO': 'update', 'SPRING_JPA_OPEN_IN_VIEW': 'false',
        'SERVER_ADDRESS': '127.0.0.1', 'SERVER_PORT': '8088',
        'SPRING_SERVLET_MULTIPART_MAX_FILE_SIZE': '20MB', 'SPRING_SERVLET_MULTIPART_MAX_REQUEST_SIZE': '21MB',
        'BLOCKCHAIN_RPC_URL': 'http://127.0.0.1:8548', 'BLOCKCHAIN_EXPECTED_CHAIN_ID': '1337',
        'WALLET_DATA_DIR': str(state), 'WALLET_SHARE_BASE_URL': f'http://127.0.0.1:{http_port}',
        'DMS_STORAGE_LOCATION': str(state / 'legacy/files'), 'DMS_BACKUP_LOCATION': str(state / 'legacy/backups'),
        'DMS_EXTERNAL_AI_ENABLED': 'false', 'OPENROUTER_API_KEY': '', 'OPENROUTER_MODEL': 'disabled',
        'FOLI_ENABLED': 'true', 'FOLI_OLLAMA_URL': 'http://127.0.0.1:11434',
        'FOLI_MODEL': env.get('FOLI_MODEL', 'qwen3:4b-instruct'),
        'FOLI_TESSERACT': '/usr/bin/tesseract', 'FOLI_OCR_DATA_DIR': '/usr/share/tesseract-ocr/5/tessdata',
        'FOLI_LAYOUT_PYTHON': sys.executable, 'FOLI_LAYOUT_SCRIPT': str(ROOT / 'tools/ocr-layout-worker.py'),
        'FOLI_TEMP_DIR': str(state / 'foli/tmp'),
        'LOGGING_LEVEL_ORG_APACHE_PDFBOX': 'OFF', 'LOGGING_LEVEL_ORG_SPRINGFRAMEWORK_AI': 'OFF',
        'SERVER_TOMCAT_ACCESSLOG_ENABLED': 'false',
        'SPRING_BOOT_API_BASE_URL': 'http://127.0.0.1:8088',
        'PUBLIC_EVM_RPC_URL': f'http://127.0.0.1:{rpc_port}',
        'WALLET_TRUST_FILE': str(state / 'trusted-deployment.json'),
        'DJANGO_ALLOWED_HOSTS': 'localhost,127.0.0.1', 'DJANGO_DEBUG': 'true',
        'DJANGO_SETTINGS_MODULE': 'hermes.settings', 'STATIC_ROOT': str(ROOT / 'static'),
        'FOLIOLET_CONTAINER': '1', 'FOLIOLET_INTAKE_FOLDER': '/app/imports/foliolet',
        'PYTHONPATH': str(ROOT / 'django-service'), 'PYTHONUNBUFFERED': '1',
        'NODE_PATH': str(ROOT / 'spring-boot-service/node_modules'),
    })
    return env


class Stack:
    def __init__(self, env):
        self.env = env
        self.children = []
        self.stopped = threading.Event()

    def start(self, name, arguments, cwd=ROOT):
        print('[start] ' + name, flush=True)
        process = subprocess.Popen(arguments, cwd=cwd, env=self.env, start_new_session=True)
        self.children.append((name, process))
        return process

    def alive(self):
        for name, process in self.children:
            if process.poll() is not None:
                raise RuntimeError(name + ' stopped (exit ' + str(process.returncode) + ')')

    def wait_for(self, name, probe, seconds=120):
        deadline, last_log = time.monotonic() + seconds, 0
        while not self.stopped.is_set():
            self.alive()
            try:
                if probe(): return
            except (OSError, ValueError): pass
            now = time.monotonic()
            if now >= deadline: raise TimeoutError(name + ' readiness timed out')
            if now - last_log > 10:
                print('[wait] ' + name, flush=True); last_log = now
            self.stopped.wait(1)
        raise InterruptedError()

    def command(self, name, arguments):
        process = self.start(name, arguments)
        while process.poll() is None:
            if self.stopped.wait(0.5): raise InterruptedError()
        self.children.remove((name, process))
        if process.returncode: raise RuntimeError(name + ' failed (exit ' + str(process.returncode) + ')')

    def model(self):
        finished, errors = threading.Event(), []
        def install():
            try:
                prepare(self.env['FOLI_MODEL'], stopped=self.stopped.is_set,
                        log=lambda message: print(message, flush=True))
            except Exception as exc: errors.append(exc)
            finally: finished.set()
        threading.Thread(target=install, daemon=True).start()
        while not finished.wait(0.5):
            if self.stopped.is_set(): raise InterruptedError()
            self.alive()
        if errors: raise errors[0]

    def close(self):
        for _, process in reversed(self.children):
            if process.poll() is None:
                try: os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError: pass
        deadline = time.monotonic() + 20
        for _, process in reversed(self.children):
            try: process.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
        self.children.clear()


def api_ready():
    try:
        HTTP.open('http://127.0.0.1:8088/api/wallet/documents', timeout=2).close()
    except HTTPError as exc:
        return exc.code == 401
    return False


def evm_ready():
    with HTTP.open(Request('http://127.0.0.1:8548',
            data=b'{"jsonrpc":"2.0","id":1,"method":"eth_chainId","params":[]}',
            headers={'Content-Type': 'application/json'}), timeout=2) as response:
        return json.load(response).get('result') == '0x539'


def main():
    os.umask(0o077)
    STATE.mkdir(parents=True, exist_ok=True)
    marker = STATE / 'container-ready.json'
    marker.unlink(missing_ok=True)
    stack = Stack(environment(os.environ))
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stack.stopped.set())
    try:
        stack.start('EVM', ['node', str(ROOT / 'tools/digilocker-evm.cjs')])
        stack.wait_for('EVM', evm_ready)
        stack.env['BLOCKCHAIN_PRIVATE_KEY'] = (STATE / 'development-relay.key').read_text().strip()
        stack.start('Spring', ['java', '-Xmx768m', '-Djava.awt.headless=true', '-jar', str(ROOT / 'spring-boot-service/app.jar')], ROOT / 'spring-boot-service')
        stack.wait_for('Spring', api_ready, seconds=180)
        stack.command('registry trust provisioning', ['node', str(ROOT / 'tools/provision-digilocker-trust.cjs')])
        stack.command('Django migrations', [sys.executable, str(ROOT / 'django-service/manage.py'), 'migrate', '--noinput'])
        stack.start('Django', [sys.executable, '-m', 'waitress', '--listen=127.0.0.1:8008', '--threads=8', 'hermes.wsgi:application'])
        stack.start('private UI/RPC entrypoint', ['nginx', '-c', str(ROOT / 'docker/nginx.conf')])
        stack.start('watcher supervisor', [sys.executable, str(ROOT / 'docker/watchers.py')])
        print('[ready] Private UI available. Preparing the local model; progress follows.', flush=True)
        stack.model()
        stack.alive()
        marker.write_text(json.dumps({'model': stack.env['FOLI_MODEL'], 'pids': [p.pid for _, p in stack.children]}))
        print('[ready] Foliolet: ' + stack.env['WALLET_SHARE_BASE_URL'] + ' — all services ready; watcher waiting for your folder pairing.', flush=True)
        while not stack.stopped.wait(2): stack.alive()
        return 0
    except InterruptedError:
        return 0
    except Exception as exc:
        print('[failed] ' + str(exc), file=sys.stderr, flush=True)
        return 1
    finally:
        marker.unlink(missing_ok=True)
        stack.close()


if __name__ == '__main__':
    sys.exit(main())
