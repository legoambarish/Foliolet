"""Idle until holder consent writes a short-lived pairing to the private control volume."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

QUEUE = Path('/pairings')
STATE = Path('/watcher-state')
FOLDER = '/host/intake/documents-inbox'

def validate(file):
    if file.is_symlink() or file.stat().st_size > 16384:
        raise ValueError('Invalid pairing file')
    data = json.loads(file.read_text())
    if str(uuid.UUID(data['sessionId'])) != file.stem or data['folder'] != FOLDER:
        raise ValueError('Wrong session or folder')
    if data['apiUrl'] != 'http://127.0.0.1:8088' or data['folderHash'] != hashlib.sha256(FOLDER.encode()).hexdigest():
        raise ValueError('Pairing must use the private local application')
    expiry = datetime.fromisoformat(data['expiresAt'].replace('Z','+00:00')).timestamp()
    if not time.time() < expiry <= time.time() + 630:
        raise ValueError('Pairing expired or outside its allowed lifetime')
    return data['sessionId']

def main():
    children = {}
    stopping = False
    def stop(*_):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print('Watcher ready; waiting for holder consent in Foliolet.', flush=True)
    try:
        while not stopping:
            STATE.joinpath('heartbeat').touch()
            for name, child in list(children.items()):
                if child.poll() is not None:
                    del children[name]
                    source = QUEUE / (name + '.json')
                    if source.is_file() and not source.is_symlink():
                        source.rename(QUEUE / (name + '.done'))
            for file in sorted(QUEUE.glob('*.json')):
                if file.stem in children: continue
                try:
                    name = validate(file)
                    if len(children) >= 8: break
                    children[name] = subprocess.Popen([sys.executable, '/app/tools/local-watcher/intake.py',
                        '--config', str(file), '--state-dir', str(STATE/name)])
                except (ValueError, KeyError, OSError, TypeError):
                    # Retain rejected bytes without echoing a capability or private path.
                    if not file.is_symlink(): file.rename(file.with_suffix('.refused'))
                    print('An expired or invalid pairing was retained and refused.', flush=True)
            time.sleep(1)
    finally:
        for child in children.values(): child.terminate()
        for child in children.values():
            try: child.wait(timeout=8)
            except subprocess.TimeoutExpired: child.kill(); child.wait()

if __name__ == '__main__': main()
