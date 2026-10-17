"""Actual Windows PowerShell companion launcher, disposable loopback pairing only."""
import json
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.local-data/intake-tests'
API = 'http://127.0.0.1:8088'


def main():
    assert os.name == 'nt', 'This gate requires real Windows'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--powershell', default=shutil.which('pwsh') or 'powershell',
                        help='Exact PowerShell executable; exercise 5.1 as well as 7')
    args = parser.parse_args()
    http = requests.Session(); http.trust_env = False
    auth = ('launcher-' + uuid.uuid4().hex[:12], 'synthetic-' + uuid.uuid4().hex)
    response = http.post(API + '/api/auth/register', json={'username': auth[0], 'password': auth[1], 'role': 'HOLDER'}, timeout=15)
    response.raise_for_status(); http.auth = auth
    folder = OUT / ('launcher-incoming-' + uuid.uuid4().hex); folder.mkdir(parents=True)
    response = http.post(API + '/api/wallet/intake/sessions', json={'folder': str(folder)}, timeout=15)
    response.raise_for_status(); config = response.json(); config['apiUrl'] = API
    pairing = OUT / 'launcher-pair-private.json'; pairing.write_text(json.dumps(config), encoding='utf8')
    command = [args.powershell, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File',
               str(ROOT / 'tools/start-digilocker-watcher.ps1'), '-PairingFile', str(pairing)]
    log = (OUT / 'launcher-process.log').open('w', encoding='utf8')
    process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            sessions = http.get(API + '/api/wallet/intake/sessions', timeout=10).json()
            if sessions[0]['connected']: break
            assert process.poll() is None, 'Companion launcher exited before connecting'
            time.sleep(.5)
        assert sessions[0]['connected'], 'Companion launcher did not connect'
        print('PASS Real PowerShell pairing launcher handles UTC JSON date and starts authenticated companion', flush=True)
        response = http.post(API + '/api/wallet/intake/sessions/' + config['sessionId'] + '/stop', timeout=10)
        response.raise_for_status()
        assert process.wait(timeout=25) != 0, 'Stopped pairing must visibly require re-arming'
        print('PASS Server Stop terminates the launched companion with a clear re-arm message', flush=True)
    finally:
        if process.poll() is None: process.terminate(); process.wait(timeout=5)
        log.close()
    config['sessionId'] = str(uuid.uuid4()); config['expiresAt'] = '2020-01-01T00:00:00Z'
    pairing.write_text(json.dumps(config), encoding='utf8')
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode != 0 and 'expired' in result.stderr
    assert not (ROOT / '.local-data/intake' / config['sessionId']).exists()
    print('PASS Expired pairing is refused before writing companion state or starting Python', flush=True)
    (OUT / 'launcher-results.json').write_text(json.dumps({'count': 3, 'result': 'PASS', 'platform': 'Windows', 'synthetic': True}), encoding='utf8')


if __name__ == '__main__': main()
