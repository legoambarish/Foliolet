"""Resume holder-consented watchers, replace old pairings, and stop with the app."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'django-service'))
from dashboard.managed_intake import validate

HTTP = build_opener(ProxyHandler({}))


def active(config):
    body = ('folderHash=' + config['folderHash']).encode()
    try:
        with HTTP.open(Request(config['apiUrl'] + '/api/intake-agent/heartbeat', data=body,
                headers={'Content-Type': 'application/x-www-form-urlencoded', 'Authorization': 'Bearer ' + config['token']}), timeout=5) as response:
            return json.load(response).get('active') is True
    except HTTPError as exc:
        if exc.code in (401, 403, 404): return False
        raise


def stop(process):
    if process.poll() is None:
        try: os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError: return
        try: process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait(timeout=3)


class Watchers:
    def __init__(self, directory, folder):
        self.directory, self.folder = Path(directory), Path(folder)
        self.children, self.parked, self.retry = {}, {}, {}

    def reconcile(self):
        found = {}
        for file in self.directory.glob('*.json'):
            try:
                if file.is_symlink() or file.stat().st_size > 8192: continue
                config = validate(json.loads(file.read_text()), self.folder)
                found[file.stem] = (file, config)
            except (OSError, ValueError, TypeError): continue
        for slot, (session, process, log) in list(self.children.items()):
            if slot not in found or found[slot][1]['sessionId'] != session or process.poll() is not None:
                stop(process); log.close(); del self.children[slot]
        for slot, (file, config) in found.items():
            session = config['sessionId']
            if slot in self.children or self.parked.get(slot) == session or time.monotonic() < self.retry.get(slot, 0): continue
            try:
                if not active(config):
                    self.parked[slot] = session
                    print('[watcher] Pairing stopped or revoked; waiting for a new pairing.', flush=True)
                    continue
                state = self.directory / 'state' / session
                state.mkdir(parents=True, exist_ok=True, mode=0o700)
                log = (state / 'companion.log').open('ab')
                try:
                    process = subprocess.Popen([sys.executable, str(ROOT / 'tools/local-watcher/intake.py'),
                        '--config', str(file), '--state-dir', str(state), '--poll', '--app-pid', str(os.getpid())],
                        stdout=log, stderr=log, start_new_session=True)
                except Exception:
                    log.close(); raise
                self.children[slot] = (session, process, log)
                print('[watcher] Managed companion started; no timer.', flush=True)
                self.retry[slot] = time.monotonic() + 10
            except (OSError, ValueError):
                self.retry[slot] = time.monotonic() + 10
                print('[watcher] Local connection unavailable; retrying.', flush=True)

    def close(self):
        for _, process, log in self.children.values():
            stop(process); log.close()
        self.children.clear()


def main():
    os.umask(0o077)
    stopped = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM): signal.signal(signum, lambda *_: stopped.set())
    manager = Watchers(ROOT / '.local-data/managed-intake', os.environ['FOLIOLET_INTAKE_FOLDER'])
    print('[watcher] Ready. Pair your mounted folder in Enroll once; later launches resume it automatically.', flush=True)
    try:
        while not stopped.is_set():
            manager.reconcile(); stopped.wait(2)
    finally: manager.close()


if __name__ == '__main__': main()
