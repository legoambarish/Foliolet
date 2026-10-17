"""Disposable native Windows companion tests; no real account or network access."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import requests
from Crypto.Hash import keccak

sys.path.insert(0, str(Path(__file__).parent / 'local-watcher'))
from intake import Companion, AppLifetime, LoopbackSession, BoundedEvents, local_origin, safe_path, stable_bytes
from watch import IntakeHandler, message


class Response:
    def __init__(self, status=200, data=None):
        self.status_code, self.data = status, data or {}
    def json(self): return self.data
    def raise_for_status(self):
        if self.status_code >= 400: raise requests.HTTPError(response=self)


class Transport:
    def __init__(self):
        self.uploads = []
        self.observed = {}
        self.fail_upload = False
        self.lose_observation_ack = False
        self.rejected = set()
        self.after_observation = None
        self.revoked = False
    def post(self, url, **kw):
        if self.revoked: return Response(401)
        if url.endswith('/heartbeat'): return Response()
        if url.endswith('/observations'):
            record = kw['json']
            raw = message(record)
            digest = '0x' + keccak.new(digest_bits=256, data=raw).hexdigest()
            key = record['sequence']
            if key in self.observed:
                assert self.observed[key]['digest'] == digest
            self.observed[key] = {'observationId': 'synthetic-' + str(key), 'sequence': key, 'digest': digest}
            if self.after_observation: self.after_observation()
            if self.lose_observation_ack:
                self.lose_observation_ack = False
                raise requests.ConnectionError('Synthetic lost acknowledgement')
            return Response(data=self.observed[key])
        assert url.endswith('/upload')
        assert kw['allow_redirects'] is False
        content = kw['files']['file'][1]
        assert hashlib.sha256(content).hexdigest() == kw['data']['sha256']
        if self.fail_upload:
            self.fail_upload = False
            return Response(503)
        if kw['data']['relativePath'] in self.rejected: return Response(409)
        self.uploads.append((kw['data'], content))
        return Response(data={'id': 'synthetic', 'sha256': kw['data']['sha256']})


class WatcherTests(unittest.TestCase):
    def test_app_lifetime_has_no_timer_and_stops_with_app(self):
        self.config['expiresAt'] = None
        self.config['lifetime'] = 'app'
        self.config['maxFiles'] = 0
        running = [True]
        companion = Companion(self.config, self.base / 'app-state', self.http, app_running=lambda: running[0])
        with patch('intake.time.time', return_value=time.time() + 86400):
            self.assertTrue(companion.active())
        for n in range(11):
            self.assertTrue(companion.enqueue(self.write('app-'+str(n)+'.txt', str(n).encode()), 0))
        running[0] = False
        self.assertFalse(companion.active())
        self.assertFalse(companion.flush())
        with self.assertRaises(ValueError):
            Companion(self.config, self.base / 'unbound', self.http)

    @unittest.skipUnless(os.name == 'nt', 'Windows process handles')
    def test_process_handle_detects_app_exit(self):
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            lifetime = AppLifetime([process.pid])
            self.assertTrue(lifetime.active())
            process.terminate(); process.wait(timeout=5)
            self.assertFalse(lifetime.active())
            lifetime.close()
        finally:
            if process.poll() is None: process.terminate(); process.wait(timeout=5)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'incoming'
        self.root.mkdir()
        self.state = self.base / 'private-state'
        self.config = {'apiUrl': 'http://127.0.0.1:8088', 'folder': str(self.root),
            'folderHash': hashlib.sha256(str(self.root).encode()).hexdigest(), 'agentId': 'synthetic-agent',
            'sessionId': 'synthetic-session', 'secret': '0x' + '11' * 32, 'token': '22' * 32, 'maxFiles': 10,
            'createdAt': (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
            'expiresAt': (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()}
        self.http = Transport()
        self.companion = Companion(self.config, self.state, self.http)
    def write(self, name='marks.txt', content=b'Math: 90\n'):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path
    def test_recursive_finished_file_exact_bytes_duplicate_and_untouched_source(self):
        path = self.write('semester/nested/marks.txt')
        before = path.stat().st_mtime_ns
        self.assertTrue(self.companion.enqueue(path, 0))
        self.assertFalse(self.companion.enqueue(path, 0))
        self.companion.flush()
        self.assertEqual(1, len(self.http.uploads))
        self.assertEqual(b'Math: 90\n', self.http.uploads[0][1])
        self.assertEqual(before, path.stat().st_mtime_ns)
        self.assertEqual(b'Math: 90\n', path.read_bytes())
        self.assertFalse(self.companion.enqueue(path, 0))
        self.assertFalse(list(self.state.glob('*.stage')))
    def test_partials_rename_old_hidden_and_unsupported_files(self):
        for name in ('x.pdf.crdownload', 'x.part', 'x.tmp', '.secret.txt', 'secret.docx'):
            with self.assertRaises(ValueError): self.companion.enqueue(self.write(name), 0)
        incomplete = self.write('incomplete.pdf', b'%PDF-1.7\nnot complete')
        with self.assertRaises(OSError): self.companion.enqueue(incomplete, 0)
        completed = self.root / 'complete.pdf'
        incomplete.write_bytes(b'%PDF-1.7\nsynthetic invalid but complete envelope\n%%EOF')
        incomplete.rename(completed)
        self.assertTrue(self.companion.enqueue(completed, 0))
        old = self.write('old.txt')
        stamp = time.time() - 100
        os.utime(old, (stamp, stamp))
        self.assertFalse(self.companion.enqueue(old, 0))
    def test_changed_during_sampling_and_windows_writer_lock_are_retried(self):
        path = self.write()
        with patch('intake.time.sleep', side_effect=lambda _: path.write_bytes(b'Math: 95\n')):
            with self.assertRaises(OSError): stable_bytes(self.root, path, 0)
        if os.name == 'nt':
            with path.open('wb') as active_writer:
                active_writer.write(b'Math: 90\n'); active_writer.flush()
                with self.assertRaises(OSError): stable_bytes(self.root, path, 0)
    def test_disconnect_restart_and_lost_observation_ack_reuse_identical_record(self):
        path = self.write()
        self.companion.enqueue(path, 0)
        self.http.lose_observation_ack = True
        self.assertFalse(self.companion.flush())
        resumed = Companion(self.config, self.state, self.http)
        self.http.fail_upload = True
        with self.assertRaises(requests.HTTPError): resumed.flush()
        resumed = Companion(self.config, self.state, self.http)
        resumed.flush()
        self.assertEqual(1, len(self.http.observed))
        self.assertEqual(1, len(self.http.uploads))
        self.assertEqual(1, resumed.agent.state['sequence'])
    def test_crash_between_stage_and_queue_save_is_recovered(self):
        path = self.write()
        with patch.object(self.companion, 'save', side_effect=OSError('Synthetic process crash')):
            with self.assertRaises(OSError): self.companion.enqueue(path, 0)
        resumed = Companion(self.config, self.state, self.http)
        self.assertTrue(resumed.enqueue(path, 0))
        resumed.flush()
        self.assertEqual(1, len(self.http.uploads))
    def test_tamper_after_observation_blocks_old_snapshot_and_accepts_new_version(self):
        path = self.write()
        self.companion.enqueue(path, 0)
        self.http.after_observation = lambda: path.write_bytes(b'Math: 95\n')
        self.companion.flush()
        self.assertFalse(self.http.uploads)
        self.assertTrue(next(iter(self.companion.state['pending'].values()))['blocked'])
        self.http.after_observation = None
        self.assertTrue(self.companion.enqueue(path, 0))
        self.companion.flush()
        self.assertEqual([b'Math: 95\n'], [v[1] for v in self.http.uploads])
    def test_damaged_or_permanently_refused_stage_does_not_block_other_downloads(self):
        one = self.write('one.txt', b'Math: 90\n')
        two = self.write('two.txt', b'Math: 95\n')
        self.companion.enqueue(one, 0); self.companion.enqueue(two, 0)
        stage = self.state / (hashlib.sha256(one.read_bytes()).hexdigest() + '.stage')
        self.assertNotIn(b'Math', stage.read_bytes())
        stage.write_bytes(b'damaged')
        self.companion.flush()
        self.assertEqual(1, len(self.http.uploads))
        three = self.write('three.txt', b'Science: 80\n')
        four = self.write('four.txt', b'Science: 85\n')
        self.http.rejected.add('three.txt')
        self.companion.enqueue(three, 0); self.companion.enqueue(four, 0)
        self.companion.flush()
        self.assertEqual(2, len(self.http.uploads))
    def test_root_binding_expiry_revocation_and_private_state(self):
        with self.assertRaises(ValueError): Companion({**self.config, 'folderHash': 'forged'}, self.state, self.http)
        with self.assertRaises(ValueError): Companion(self.config, self.root / 'state', self.http)
        self.companion.expiry = time.time() - 1
        self.assertFalse(self.companion.enqueue(self.write(), 0))
        self.assertFalse(self.companion.flush())
        self.companion.expiry = time.time() + 100
        self.http.revoked = True
        with self.assertRaises(PermissionError): self.companion.flush()
    def test_folder_escape_symlink_and_native_windows_junction_rejected(self):
        outside = self.base / 'outside'; outside.mkdir(); external = outside / 'external.txt'; external.write_bytes(b'private')
        with self.assertRaises(ValueError): safe_path(self.root, external)
        junction = self.root / 'escape'
        if os.name == 'nt':
            result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(outside)], capture_output=True)
            self.assertEqual(0, result.returncode)
            self.addCleanup(lambda: junction.rmdir() if junction.exists() else None)
            with self.assertRaises(ValueError): stable_bytes(self.root, junction / 'external.txt', 0)
        else:
            junction.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError): stable_bytes(self.root, junction / 'external.txt', 0)
    def test_event_queue_and_ten_file_limit_are_bounded(self):
        pending = BoundedEvents(); handler = IntakeHandler(pending)
        handler.on_created(SimpleNamespace(is_directory=False, src_path='created'))
        handler.on_modified(SimpleNamespace(is_directory=False, src_path='modified'))
        handler.on_moved(SimpleNamespace(is_directory=False, dest_path='renamed'))
        self.assertEqual(['created', 'modified', 'renamed'], [pending.get_nowait() for _ in range(3)])
        for n in range(1000): pending.put(n)
        self.assertEqual(128, pending.qsize())
        for n in range(10): self.assertTrue(self.companion.enqueue(self.write(str(n)+'.txt', str(n).encode()), 0))
        self.assertFalse(self.companion.enqueue(self.write('eleven.txt', b'eleven'), 0))
    def test_loopback_transport_never_uses_proxy_redirect_or_other_origin(self):
        for value in ('https://127.0.0.1:8088', 'http://localhost:8088', 'http://evil.example:8088', 'http://127.0.0.1:8088/api', 'http://user:pass@127.0.0.1:8088'):
            with self.assertRaises(ValueError): local_origin(value)
        http = LoopbackSession('http://127.0.0.1:8088')
        self.assertFalse(http.trust_env)
        with self.assertRaises(ValueError): http.post('http://127.0.0.1:9099/api')
        with patch.object(requests.Session, 'request', return_value=Response()) as request:
            http.post('http://127.0.0.1:8088/api', allow_redirects=True)
            self.assertFalse(request.call_args.kwargs['allow_redirects'])


if __name__ == '__main__': unittest.main(verbosity=2)
