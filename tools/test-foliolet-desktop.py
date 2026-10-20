"""Windows startup acceptance for an idle demo with no concurrent users/writes.

This suite deliberately stops and restarts the owned services. Do not run it
while someone is using the application.
"""
import ctypes
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import socket
from pathlib import Path
import subprocess
import sys
import threading
import time

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.local-data' / 'desktop-tests'
ENGINE = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
CHECKS = []
RUNTIME = json.loads((ROOT / '.local-data/intake-runtime.json').read_text(encoding='utf-8-sig'))
PORTS = RUNTIME.get('ports', {'ui':8008,'api':8088,'evm':8548,'pg':55438,'receiver':8001,'control':8002})
UI = 'http://127.0.0.1:' + str(PORTS['ui'])
API = 'http://127.0.0.1:' + str(PORTS['api'])


def pass_check(name):
    CHECKS.append({'name': name, 'result': 'PASS'})
    print(datetime.now().astimezone().strftime('%H:%M:%S'), 'PASS', name, flush=True)


def run(script='start-foliolet.ps1', *args, expected=0, timeout=240):
    name = str(len(list(OUT.glob('run-*.log'))))
    log_path = OUT / ('run-' + name + '.log')
    with log_path.open('w', encoding='utf8') as log:
        process = subprocess.Popen([str(ENGINE), '-NoProfile', '-ExecutionPolicy', 'Bypass', '-STA', '-File',
                                    str(ROOT / 'tools' / script), *args], cwd=ROOT, stdout=log, stderr=log,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        deadline = time.monotonic() + timeout
        next_heartbeat = time.monotonic() + 15
        while process.poll() is None:
            assert time.monotonic() < deadline, f'{script} exceeded deadline; inspect {log_path}'
            if time.monotonic() > next_heartbeat:
                print(datetime.now().astimezone().strftime('%H:%M:%S'), 'ACTIVE', script, flush=True)
                next_heartbeat = time.monotonic() + 15
            time.sleep(.25)
    assert (process.returncode == 0) == (expected == 0), log_path.read_text(encoding='utf8', errors='replace')
    return log_path


def snapshot():
    # Only compare hashes/counts. Never export any retained keys or documents.
    paths = [p for p in (ROOT / '.local-data').rglob('*') if p.is_file() and
             (p.suffix in ('.key', '.address') or p.is_relative_to(ROOT / '.local-data/wallet')
              or p.name in ('selective-registry.json', 'trusted-deployment.json'))]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def processes():
    value = json.loads((ROOT / '.local-data/intake-processes.json').read_text(encoding='utf-8-sig'))
    return {item['name']: (item['pid'], item['started']) for item in value}


def receiver_status():
    sys.path.insert(0, str(ROOT / 'django-service'))
    from dashboard import tunnel_manager
    cfg = dict(tunnel_manager.config(), port=PORTS['receiver'], control=PORTS['control'])
    return tunnel_manager.rpc('status', cfg)


def process_running(pid):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    try:
        code = ctypes.c_uint32()
        assert kernel.GetExitCodeProcess(handle, ctypes.byref(code))
        return code.value == 259
    finally:
        kernel.CloseHandle(handle)


def main():
    assert os.name == 'nt'
    OUT.mkdir(parents=True, exist_ok=True)
    baseline = snapshot()
    assert baseline, 'Expected retained isolated keys before this regression run'
    run('start-foliolet.ps1', '-CheckOnly', '-StatusPath', str(OUT / 'health.json'))
    pass_check('Built-in Windows PowerShell recognizes actual owned services, Python child and PostgreSQL slash paths')
    before = processes()
    repeat = run('start-foliolet.ps1', '-StatusPath', str(OUT / 'repeat.json'))
    assert before == processes()
    assert 'Installing the project Python dependencies' not in repeat.read_text(encoding='utf8')
    pass_check('Repeated start accepts current requirement pins without reinstalling or changing service PIDs')

    # Hold the exact worker mutex from another process/thread, then verify refusal.
    identity = hashlib.sha256(str(ROOT).lower().encode('utf8')).hexdigest().upper()[:20]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    kernel.ReleaseMutex.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.CreateMutexW(None, True, 'Local\\FolioletStart-' + identity)
    assert handle
    try:
        run('start-foliolet.ps1', '-StatusPath', str(OUT / 'busy.json'), expected=1)
        assert 'already starting' in json.loads((OUT / 'busy.json').read_text())['message']
        assert before == processes()
    finally:
        kernel.ReleaseMutex(handle); kernel.CloseHandle(handle)
    pass_check('Concurrent startup is refused without creating duplicate service processes')

    assert baseline == snapshot(), 'Runtime data changed during testing; stop before the restart checks and use an idle demo'
    public_before = receiver_status()
    assert public_before['state'] == 'ready'
    run('start-foliolet.ps1', '-Stop', '-StatusPath', str(OUT / 'stop.json'))
    assert baseline == snapshot()
    pass_check('One-action Stop retains every recorded original, signing/encryption key and registry pin')
    for port in PORTS.values():
        with socket.socket() as client:
            client.settimeout(1)
            assert client.connect_ex(('127.0.0.1', port)) != 0, f'Port {port} still listening after Stop'
    pass_check('Stop closes configured app, database, public receiver and control ports')
    for key in ('supervisorPid', 'tunnelPid'):
        assert public_before[key] and not process_running(public_before[key]), f'{key} still running after Stop'
    pass_check('Stop terminates the original detached supervisor and Cloudflare process')
    run('start-foliolet.ps1', '-Stop', '-StatusPath', str(OUT / 'stop-again.json'))
    pass_check('Repeated Stop succeeds with the receiver and services already stopped')

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b'owned by the test')
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', PORTS['ui']), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        run('start-foliolet.ps1', '-StatusPath', str(OUT / 'occupied.json'), expected=1)
        assert 'another process' in json.loads((OUT / 'occupied.json').read_text())['message']
        http = requests.Session(); http.trust_env = False
        assert http.get(UI + '/', timeout=5).text == 'owned by the test'
        assert baseline == snapshot()
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)
    pass_check('Foreign occupied port is refused without stopping it or changing retained application state')

    if '--headless' in sys.argv:
        run('start-foliolet.ps1', '-StatusPath', str(OUT / 'cold-start.json'), timeout=360)
        result = json.loads((OUT / 'cold-start.json').read_text())
        assert result['state'] == 'ready' and result['url'] == UI + '/'
    else:
        run('launch-foliolet.ps1', '-NoBrowser', '-SmokeTest', '-CapturePath', str(OUT / 'cold start.png'), timeout=360)
        result = json.loads((ROOT / '.local-data/desktop-ui-result.json').read_text())
        assert result['state'] == 'ready' and not result['browserOpened']
        assert (OUT / 'cold start.png').stat().st_size > 1000
    run('start-foliolet.ps1', '-CheckOnly', '-StatusPath', str(OUT / 'cold-health.json'))
    assert baseline == snapshot()
    assert json.loads((ROOT / '.local-data/intake-runtime.json').read_text(encoding='utf-8-sig'))['ports'] == PORTS
    pass_check('Cold launcher start retains saved ports, originals, keys and registry pins')

    before = processes()
    if '--headless' in sys.argv:
        run('start-foliolet.ps1', '-StatusPath', str(OUT / 'warm-start.json'))
    else:
        run('launch-foliolet.ps1', '-NoBrowser', '-SmokeTest', '-CapturePath', str(OUT / 'warm start.png'))
    assert before == processes()
    pass_check('Warm desktop launch shows ready state and preserves service PIDs')

    http = requests.Session(); http.trust_env = False
    login = http.get(UI + '/login/', timeout=10)
    assert login.status_code == 200 and 'csrfmiddlewaretoken' in login.text
    assert http.get(API + '/api/wallet', timeout=10).status_code == 401
    for port in (PORTS['receiver'], PORTS['control']):
        with socket.create_connection(('127.0.0.1', port), timeout=3): pass
    pass_check('Public receiver and control listener return after cold restart')
    public_after = receiver_status()
    assert public_after['state'] == 'ready' and public_after['instance'] != public_before['instance']
    pass_check('Cold restart establishes a new ready public tunnel instance')
    assert all(item['result'] == 'PASS' for item in CHECKS)
    pass_check('Readiness checks actual login UI and protected backend after a cold restart')
    (OUT / 'results.json').write_text(json.dumps({'generatedAt': datetime.now(timezone.utc).isoformat(),
        'platform': 'Windows', 'engine': 'Windows PowerShell 5.1', 'result': 'PASS',
        'count': len(CHECKS), 'checks': CHECKS}, indent=2) + '\n', encoding='utf8')
    print('PASS', len(CHECKS), 'desktop startup acceptance checks', flush=True)


def status_io():
    """Exercise the sharing/atomic-replacement race with two real PS5 processes."""
    OUT.mkdir(parents=True, exist_ok=True)
    writer = OUT / 'status-writer.ps1'
    reader = OUT / 'status-reader.ps1'
    (OUT / 'io.json').write_text('{"counter": -1}', encoding='utf8')
    writer.write_text("""$ErrorActionPreference='Stop'
. .\\tools\\foliolet-desktop-common.ps1
$path=Join-Path $folioletData 'desktop-tests\\io.json'
for ($counter=0; $counter -le 100; $counter++) {
    Write-FolioletJson $path @{counter=$counter}
    Start-Sleep -Milliseconds 2
}
""", encoding='utf8')
    reader.write_text("""$ErrorActionPreference='Stop'
. .\\tools\\foliolet-desktop-common.ps1
$path=Join-Path $folioletData 'desktop-tests\\io.json'
$last=-1
for ($attempt=0; $attempt -lt 1000; $attempt++) {
    $value=Read-FolioletJson $path
    if ($value) {
        if ($value.counter -lt $last) { throw 'Status went backwards' }
        $last=$value.counter
        if ($last -eq 100) { exit 0 }
    }
    Start-Sleep -Milliseconds 2
}
throw 'Status reader never saw completion'
""", encoding='utf8')
    logs=[]; jobs=[]
    try:
        for path in (reader, writer):
            log=(OUT/(path.stem+'.log')).open('w',encoding='utf8'); logs.append(log)
            jobs.append(subprocess.Popen([str(ENGINE),'-NoProfile','-ExecutionPolicy','Bypass','-File',str(path)],
                cwd=ROOT,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW))
        for job in jobs:
            assert job.wait(timeout=40)==0, 'Concurrent status test failed; inspect desktop-tests/status-*.log'
    finally:
        for log in logs: log.close()
    assert json.loads((OUT/'io.json').read_text())['counter']==100
    result={'result':'PASS','count':1,'updates':101,'engine':'Windows PowerShell 5.1',
            'check':'Concurrent status reading and atomic replacement completes without a sharing error'}
    (OUT/'status-io-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print('PASS Concurrent status reading and atomic replacement: 101 updates',flush=True)


if __name__ == '__main__':
    if '--status-io-only' in sys.argv: status_io()
    else: main()
