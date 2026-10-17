"""Opt-in private document intake companion, bound to Foliolet's lifetime.

Download a pairing file from Foliolet's Enroll page, then:
  python tools/local-watcher/intake.py --config PATH_TO_PAIRING_FILE
Only new/changed files received while armed are eligible. Ctrl+C stops locally.
Foliolet's Stop button also revokes the capability. Source downloads are untouched.
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
import queue
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests
from Crypto.Cipher import AES
from watchdog.observers import Observer
from watch import Agent, IntakeHandler
from local_files import MAX_BYTES, SUFFIXES, safe_path, stable_bytes

class LoopbackSession(requests.Session):
    def __init__(self, origin):
        super().__init__()
        self.origin = local_origin(origin)
        self.trust_env = False

    def request(self, method, url, **kwargs):
        if local_origin(urlsplit(url)._replace(path='', query='', fragment='').geturl()) != self.origin:
            raise ValueError('Non-loopback or different-origin transport refused')
        kwargs['allow_redirects'] = False
        return super().request(method, url, **kwargs)


def local_origin(value):
    u = urlsplit(value)
    if (u.scheme != 'http' or u.hostname not in ('127.0.0.1', '::1') or not u.port
            or u.username or u.password or u.path not in ('', '/') or u.query or u.fragment):
        raise ValueError('The companion requires a numeric loopback HTTP origin')
    return value.rstrip('/')


class AppLifetime:
    """Hold Windows process handles so a reused PID cannot extend watching."""
    def __init__(self, pids):
        if os.name != 'nt' or not pids:
            raise ValueError('App-lifetime watching requires Foliolet process IDs on Windows')
        import ctypes
        from ctypes import wintypes
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        self.kernel.OpenProcess.restype = wintypes.HANDLE
        self.kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.kernel.WaitForSingleObject.restype = wintypes.DWORD
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handles = []
        try:
            for pid in pids:
                handle = self.kernel.OpenProcess(0x00100000, False, pid)
                if not handle:
                    raise ValueError('Foliolet is not running; start it before the watcher')
                self.handles.append(handle)
            if not self.active():
                raise ValueError('Foliolet stopped before the watcher connected')
        except Exception:
            self.close()
            raise

    def active(self):
        return all(self.kernel.WaitForSingleObject(handle, 0) == 258 for handle in self.handles)

    def close(self):
        for handle in self.handles:
            self.kernel.CloseHandle(handle)
        self.handles.clear()


class Companion:
    def __init__(self, config, state_dir, transport=None, app_running=None):
        self.config = config
        self.base = local_origin(config['apiUrl'])
        self.root = Path(config['folder'])
        if not self.root.is_absolute() or not self.root.is_dir():
            raise ValueError('Create the chosen intake folder before starting')
        if self.root.name.lower() in ('downloads', 'desktop', 'documents') or len(self.root.parts) < 4:
            raise ValueError('Choose a dedicated intake subfolder')
        if hashlib.sha256(str(self.root).encode()).hexdigest() != config['folderHash']:
            raise ValueError('Folder does not match this pairing; re-arm in Foliolet to change it')
        self.expiry = (datetime.fromisoformat(config['expiresAt'].replace('Z', '+00:00')).timestamp()
                       if config.get('expiresAt') else None)
        self.app_running = app_running
        if self.expiry is None and (config.get('lifetime') != 'app' or app_running is None):
            raise ValueError('A pairing without expiry must be bound to the running Foliolet app')
        self.state_dir = Path(state_dir).resolve()
        if self.state_dir.is_relative_to(self.root.resolve()):
            raise ValueError('Keep companion state outside the intake folder')
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.http = transport or LoopbackSession(self.base)
        self.http.trust_env = False
        self.headers = {'Authorization': 'Bearer ' + config['token']}
        self.agent = Agent(self.root, config, self.state_dir / 'agent-state.json', self.http)
        self.state_file = self.state_dir / 'queue.json'
        self.state = json.loads(self.state_file.read_text()) if self.state_file.exists() else {
            'session': config['sessionId'], 'pending': {}, 'done': [],
            'started': int(datetime.fromisoformat(config['createdAt'].replace('Z', '+00:00')).timestamp() * 1e9)}
        if self.state['session'] != config['sessionId']:
            raise ValueError('This state belongs to another session')
        key_file = self.state_dir / 'stage.key'
        if not key_file.exists():
            with key_file.open('xb') as f:
                f.write(os.urandom(32))
            key_file.chmod(0o600)
        self.key = key_file.read_bytes()

    def active(self):
        return ((self.expiry is None or time.time() < self.expiry)
                and (self.app_running is None or self.app_running()))

    def save(self):
        temp = self.state_file.with_suffix('.tmp')
        temp.write_text(json.dumps(self.state), encoding='utf-8')
        os.replace(temp, self.state_file)

    def read_stage(self, digest):
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Invalid staged fingerprint')
        blob = (self.state_dir / (digest + '.stage')).read_bytes()
        if len(blob) < 33:
            raise ValueError('Incomplete encrypted stage')
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=blob[:16])
        cipher.update((self.config['sessionId'] + ':' + digest).encode())
        content = cipher.decrypt_and_verify(blob[32:], blob[16:32])
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError('Staged bytes failed their fingerprint check')
        return content

    def heartbeat(self):
        r = self.http.post(self.base + '/api/intake-agent/heartbeat', data={'folderHash': self.config['folderHash']},
                           headers=self.headers, timeout=(3, 10), allow_redirects=False)
        if r.status_code == 401:
            raise PermissionError('The session expired or was stopped. Re-arm in Foliolet.')
        r.raise_for_status()

    def enqueue(self, incoming, delay=1.0):
        if not self.active():
            return False
        path, _ = safe_path(self.root, incoming)
        # Never sweep pre-existing downloads into a newly armed session.
        if path.stat().st_mtime_ns < self.state['started']:
            return False
        relative, content = stable_bytes(self.root, incoming, delay)
        digest = hashlib.sha256(content).hexdigest()
        if digest in self.state['done'] or digest in self.state['pending']:
            return False
        limit = 0 if self.expiry is None else min(10, self.config['maxFiles'])
        if limit and len(self.state['pending']) + len(self.state['done']) >= limit:
            return False
        cipher = AES.new(self.key, AES.MODE_GCM)
        cipher.update((self.config['sessionId'] + ':' + digest).encode())
        encrypted, tag = cipher.encrypt_and_digest(content)
        staged = self.state_dir / (digest + '.stage')
        if staged.exists():
            # A crash after the durable stage but before queue.json may leave an orphan.
            # Adopt only an authenticated stage for exactly the same source bytes.
            if self.read_stage(digest) != content:
                raise ValueError('Existing stage does not match this source')
        else:
            with staged.open('xb') as f:
                f.write(cipher.nonce + tag + encrypted)
                f.flush()
                os.fsync(f.fileno())
        staged.chmod(0o600)
        self.state['pending'][digest] = {'relative': relative, 'observation': None}
        self.save()
        return True

    def flush(self):
        if not self.active():
            return False
        self.heartbeat()
        for digest, item in list(self.state['pending'].items()):
            if item.get('blocked'):
                continue
            if not self.active():
                return False
            staged = self.state_dir / (digest + '.stage')
            try:
                content = self.read_stage(digest)
            except (ValueError, OSError):
                item['blocked'] = True
                self.save()
                print('A staged file is damaged or unavailable. Other downloads can continue; import that original manually.', flush=True)
                continue
            if not item['observation']:
                # Legacy agent logs include filenames; suppress those in this privacy-scoped mode.
                with contextlib.redirect_stdout(io.StringIO()):
                    item['observation'] = self.agent.report_staged(item['relative'], content)
                self.save()
                if not item['observation']:
                    return False
            # Source substitution after observation never changes the upload's byte identity.
            # Refuse changed/deleted downloads and retain their encrypted failed evidence.
            try:
                _, current = stable_bytes(self.root, self.root / item['relative'], delay=0.1)
                if hashlib.sha256(current).hexdigest() != digest:
                    raise ValueError('Source changed')
            except (ValueError, OSError):
                item['blocked'] = True
                self.save()
                print('A download changed after staging. Its old snapshot was blocked; review the new file.', flush=True)
                continue
            filename = Path(item['relative']).name
            response = self.http.post(self.base + '/api/intake-agent/upload', headers=self.headers,
                data={'folderHash': self.config['folderHash'], 'relativePath': item['relative'],
                      'sha256': digest, 'observationId': item['observation']},
                files={'file': (filename, content, 'application/octet-stream')}, timeout=(3, 30), allow_redirects=False)
            if response.status_code == 401:
                raise PermissionError('The session expired or was stopped')
            if response.status_code in (400, 403, 404, 409, 413, 415, 422):
                item['blocked'] = True
                self.save()
                print('One download was refused. Its encrypted outbox is retained; review or import it manually.', flush=True)
                continue
            response.raise_for_status()
            if response.json().get('sha256') != digest:
                raise ValueError('Unexpected intake acknowledgement')
            self.state['done'].append(digest)
            del self.state['pending'][digest]
            self.save()
            staged.unlink()  # Only our acknowledged encrypted staging artifact, never the download.
            print('File received by Foliolet. Open the Enroll page to review it.', flush=True)
        return True


class BoundedEvents(queue.Queue):
    def __init__(self):
        super().__init__(maxsize=128)

    def put(self, item, *args, **kwargs):
        try:
            super().put(item, block=False)
        except queue.Full:
            pass  # A bounded periodic reconciliation includes only post-arm files.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--state-dir')
    parser.add_argument('--app-pid', type=int, action='append', help='Owned Foliolet process to stop with')
    parser.add_argument('--once', action='store_true', help='Flush the existing outbox and scan new files once')
    parser.add_argument('--poll', action='store_true', help='Poll host-mounted folders (Docker Desktop on macOS)')
    args = parser.parse_args()
    config_file = Path(args.config).resolve()
    config = json.loads(config_file.read_text(encoding='utf-8-sig'))
    root = Path(config['folder']).resolve()
    if config_file.is_relative_to(root):
        parser.error('Keep the pairing file outside the intake folder')
    state_dir = args.state_dir or Path(__file__).resolve().parents[2] / '.local-data/intake' / config['sessionId']
    lifetime = None
    if args.app_pid:
        if os.name == 'nt':
            lifetime = AppLifetime(args.app_pid)
        else:
            from lifetime import LinuxAppLifetime
            lifetime = LinuxAppLifetime(args.app_pid)
    companion = Companion(config, state_dir, app_running=lifetime.active if lifetime else None)
    pending = BoundedEvents()
    if args.poll:
        from watchdog.observers.polling import PollingObserver
        observer = PollingObserver(timeout=1)
    else:
        observer = Observer()
    observer.schedule(IntakeHandler(pending), str(companion.root), recursive=True)
    observer.start()
    print('Watching while Foliolet is running. No timer. Stop watching in Foliolet revokes access.'
          if companion.expiry is None else 'Watching until session expiry. Ctrl+C stops locally.', flush=True)
    print('This records holder-controlled file continuity, never issuer verification.', flush=True)
    last_scan = last_status = 0
    try:
        while companion.active():
            now = time.monotonic()
            if now - last_scan > 5:
                # Do not follow symlink directories; safe_path also rejects junction descendants.
                for folder, directories, files in os.walk(companion.root, followlinks=False):
                    directories[:] = [d for d in directories if not d.startswith('.') and not Path(folder, d).is_symlink()
                                      and not getattr(Path(folder, d).lstat(), 'st_file_attributes', 0) & 0x400]
                    for filename in files:
                        pending.put(str(Path(folder, filename)))
                last_scan = now
            try:
                incoming = pending.get(timeout=0.5)
                try:
                    companion.enqueue(incoming)
                except (ValueError, OSError):
                    pass  # Partial/locked/unsafe files are retried only through reconciliation.
            except queue.Empty:
                pass
            try:
                companion.flush()
            except requests.RequestException:
                print('Local connection unavailable; encrypted outbox retained for this session.', flush=True)
                time.sleep(2)
            if now - last_status > 10:
                print(f'Intake active: {len(companion.state["done"])} received, {len(companion.state["pending"])} pending.', flush=True)
                last_status = now
            if args.once and pending.empty():
                break
        return 0
    except KeyboardInterrupt:
        print('Local watching stopped. Use Stop watching in Foliolet to revoke the session.', flush=True)
        return 0
    except PermissionError as exc:
        print(str(exc), flush=True)
        return 1
    finally:
        observer.stop()
        observer.join(timeout=5)
        if lifetime:
            lifetime.close()


if __name__ == '__main__':
    raise SystemExit(main())
