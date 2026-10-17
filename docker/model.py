"""Install the configured local model once; verify its bounded offline runtime."""
import json
import time
from urllib.request import Request, build_opener, ProxyHandler

HTTP = build_opener(ProxyHandler({}))
BASE = 'http://127.0.0.1:11434'
MAX_BYTES = 6_000_000_000


def request(path, payload=None, timeout=10):
    data = None if payload is None else json.dumps(payload).encode()
    return HTTP.open(Request(BASE + path, data=data, headers={'Content-Type': 'application/json'}), timeout=timeout)


def json_request(path):
    with request(path) as response:
        return json.load(response)


def ready(model):
    status = json_request('/api/status')
    if status.get('cloud', {}).get('disabled') is not True:
        raise ValueError('Ollama cloud must be disabled')
    installed = next((item for item in json_request('/api/tags').get('models', [])
                      if model in (item.get('name'), item.get('model'))), None)
    if installed and not 0 < installed.get('size', 0) < MAX_BYTES:
        raise ValueError('The configured local model exceeds the package limit')
    return installed is not None


def prepare(model, stopped=lambda: False, log=print):
    deadline = time.monotonic() + 120
    while True:
        try:
            if ready(model):
                log('[model] Cached model ready; no download needed.')
                return
            break
        except (OSError, TimeoutError):
            if stopped(): raise InterruptedError()
            if time.monotonic() >= deadline: raise TimeoutError('Ollama did not start')
            time.sleep(2)
    log('[model] Downloading missing ' + model + ' into the persistent model volume…')
    last_report = -1
    with request('/api/pull', {'model': model, 'stream': True}, timeout=120) as response:
        for line in response:
            if stopped(): raise InterruptedError()
            update = json.loads(line)
            if update.get('error'): raise RuntimeError('Model download failed: ' + str(update['error']))
            total, done = update.get('total', 0), update.get('completed', 0)
            if total > MAX_BYTES: raise ValueError('Model layer exceeds the local model size limit')
            percent = int(done * 100 / total) if total else -1
            if percent >= last_report + 5 or update.get('status') == 'success':
                log('[model] ' + (str(percent) + '%' if total else update.get('status', 'Preparing')))
                last_report = percent
    if not ready(model): raise RuntimeError('Model pull finished without the configured local model')
    log('[model] Model ready. Future starts reuse this download.')
