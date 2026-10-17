"""Container control regressions, runnable without changing any live app state."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'docker'))
sys.path.insert(0, str(ROOT / 'django-service'))
sys.path.insert(0, str(ROOT / 'tools/local-watcher'))
from lifetime import LinuxAppLifetime
import bootstrap
import model
import runtime
import watchers
from dashboard import managed_intake


def config(folder, session='00000000-0000-4000-8000-000000000001'):
    return {'folder': str(folder), 'apiUrl': 'http://127.0.0.1:8088', 'sessionId': session,
            'folderHash': hashlib.sha256(str(folder).encode()).hexdigest(), 'token': '12' * 32,
            'agentId': 'synthetic-agent', 'secret': '34' * 32, 'lifetime': 'app', 'expiresAt': None}


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_persistent_secret_is_reused_and_corruption_fails_closed(self):
        bootstrap.initialize(self.root)
        file = self.root / 'postgres-password'
        self.addCleanup(lambda: file.chmod(0o600))
        original = file.read_bytes()
        bootstrap.initialize(self.root)
        self.assertEqual(file.read_bytes(), original)
        self.assertEqual(len(original), 64)
        file.chmod(0o600); file.write_text('broken')
        with self.assertRaises(ValueError): bootstrap.initialize(self.root)
        self.assertEqual(file.read_text(), 'broken')

    def test_environment_injects_private_services_secrets_and_host_ports(self):
        password = self.root / 'secret'; password.write_text('synthetic-only')
        env = runtime.environment({'FOLIOLET_HTTP_PORT': '18008', 'FOLIOLET_RPC_PORT': '18548',
                                   'OPENROUTER_API_KEY': 'must-not-be-used'}, self.root, password)
        self.assertEqual(env['SPRING_DATASOURCE_PASSWORD'], 'synthetic-only')
        self.assertEqual(env['SPRING_BOOT_API_BASE_URL'], 'http://127.0.0.1:8088')
        self.assertEqual(env['FOLI_OLLAMA_URL'], 'http://127.0.0.1:11434')
        self.assertEqual(env['PUBLIC_EVM_RPC_URL'], 'http://127.0.0.1:18548')
        self.assertEqual(env['WALLET_SHARE_BASE_URL'], 'http://127.0.0.1:18008')
        self.assertEqual(env['OPENROUTER_API_KEY'], '')
        self.assertEqual(env['DMS_EXTERNAL_AI_ENABLED'], 'false')
        with self.assertRaises(ValueError): runtime.environment({'FOLIOLET_HTTP_PORT':'8548'}, self.root, password)

    def test_failed_child_aborts_stack_instead_of_reporting_ready(self):
        stack = runtime.Stack({})
        child = Mock(); child.poll.return_value = 1; child.returncode = 1
        stack.children = [('Spring', child)]
        with self.assertRaisesRegex(RuntimeError, 'Spring stopped'): stack.alive()

    def test_shutdown_interrupts_a_blocked_model_download(self):
        stack = runtime.Stack({'FOLI_MODEL':'synthetic'})
        release = threading.Event()
        self.addCleanup(release.set)
        with patch.object(runtime, 'prepare', side_effect=lambda *a, **k: release.wait(3)):
            stack.stopped.set()
            started = time.monotonic()
            with self.assertRaises(InterruptedError): stack.model()
            self.assertLess(time.monotonic() - started, 1.5)

    def test_linux_watcher_lifetime_detects_exit_and_pid_reuse(self):
        stat = self.root / '42/stat'; stat.parent.mkdir()
        def write(state='S', started='123'):
            stat.write_text('42 (supervisor (with spaces)) ' + ' '.join([state] + ['0'] * 18 + [started]))
        write(); lifetime = LinuxAppLifetime([42], self.root)
        self.assertTrue(lifetime.active())
        write(started='124'); self.assertFalse(lifetime.active())
        write(state='Z'); self.assertFalse(lifetime.active())
        with self.assertRaises(ValueError): LinuxAppLifetime([42], self.root)
        stat.unlink(); self.assertFalse(lifetime.active())


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.installed, self.pulls, self.cloud, self.size, self.failure = False, 0, True, 2500000000, False
        fixture = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                value = {'cloud': {'disabled': fixture.cloud}} if self.path == '/api/status' else {
                    'models': [{'name':'synthetic:4b','size':fixture.size}] if fixture.installed else []}
                body = json.dumps(value).encode()
                self.send_response(200); self.end_headers(); self.wfile.write(body)
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                fixture.assertEqual(payload['model'], 'synthetic:4b')
                fixture.pulls += 1
                self.send_response(200); self.end_headers()
                if fixture.failure:
                    self.wfile.write(b'{"error":"synthetic registry failure"}\n')
                else:
                    fixture.installed = True
                    self.wfile.write(b'{"status":"pulling","total":100,"completed":50}\n{"status":"success"}\n')
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True); thread.start()
        self.addCleanup(self.server.server_close); self.addCleanup(self.server.shutdown)
        patcher = patch.object(model, 'BASE', 'http://127.0.0.1:' + str(self.server.server_port))
        patcher.start(); self.addCleanup(patcher.stop)

    def test_cold_model_download_and_warm_start_without_another_pull(self):
        logs = []
        model.prepare('synthetic:4b', log=logs.append)
        self.assertEqual(self.pulls, 1); self.assertTrue(model.ready('synthetic:4b'))
        model.prepare('synthetic:4b', log=logs.append)
        self.assertEqual(self.pulls, 1)
        self.assertTrue(any('50%' in line for line in logs))

    def test_cloud_enabled_or_oversized_model_is_rejected(self):
        self.cloud = False
        with self.assertRaises(ValueError): model.prepare('synthetic:4b', log=lambda _:None)
        self.assertEqual(self.pulls, 0)
        self.cloud = True; self.installed = True; self.size = model.MAX_BYTES
        with self.assertRaises(ValueError): model.ready('synthetic:4b')

    def test_registry_failure_is_not_reported_as_ready(self):
        self.failure = True
        with self.assertRaises(RuntimeError): model.prepare('synthetic:4b', log=lambda _:None)
        self.assertFalse(self.installed)


class WatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.folder = self.root / 'incoming'; self.folder.mkdir()
        self.manager = watchers.Watchers(self.root / 'private', self.folder)
        self.active = patch.object(watchers, 'active', return_value=True).start()
        self.stop = patch.object(watchers, 'stop').start()
        self.spawn = patch.object(watchers.subprocess, 'Popen').start()
        self.addCleanup(patch.stopall)
        self.addCleanup(self.manager.close)
        self.process = Mock(); self.process.poll.return_value = None
        self.spawn.return_value = self.process

    def save(self, holder='holder', session='00000000-0000-4000-8000-000000000001'):
        return managed_intake.save(config(self.folder, session), holder, self.manager.directory, self.folder)

    def test_auto_start_is_idempotent_and_rearm_replaces_only_its_holder(self):
        self.save(); self.manager.reconcile(); self.manager.reconcile()
        self.assertEqual(self.spawn.call_count, 1)
        self.assertIn('--poll', self.spawn.call_args.args[0])
        self.assertIn('--app-pid', self.spawn.call_args.args[0])
        self.save('another-holder', '00000000-0000-4000-8000-000000000003'); self.manager.reconcile()
        self.assertEqual(len(self.manager.children), 2)
        self.save(session='00000000-0000-4000-8000-000000000002')
        self.manager.retry.clear(); self.manager.reconcile()
        self.assertEqual(self.spawn.call_count, 3); self.stop.assert_called_once_with(self.process)
        self.assertEqual(len(self.manager.children), 2)
        self.manager.close(); self.assertEqual(self.manager.children, {})

    def test_revocation_parks_the_pairing_until_it_changes(self):
        self.save(); self.active.return_value = False
        self.manager.reconcile(); self.manager.reconcile()
        self.spawn.assert_not_called(); self.assertEqual(self.active.call_count, 1)
        self.save(session='00000000-0000-4000-8000-000000000002')
        self.active.return_value = True; self.manager.reconcile(); self.spawn.assert_called_once()

    def test_restart_reuses_the_saved_pairing_and_private_queue_location(self):
        self.save(); self.manager.reconcile()
        original = self.spawn.call_args.args[0]
        self.manager.close()
        restarted = watchers.Watchers(self.manager.directory, self.folder)
        self.addCleanup(restarted.close)
        restarted.reconcile()
        self.assertEqual(self.spawn.call_count, 2)
        self.assertEqual(self.spawn.call_args.args[0], original)
        self.assertEqual(len(restarted.children), 1)

    def test_other_folders_and_non_loopback_pairings_are_not_launched(self):
        file = self.save(); saved = json.loads(file.read_text()); saved['apiUrl'] = 'https://example.com'
        file.write_text(json.dumps(saved)); self.manager.reconcile(); self.spawn.assert_not_called()
        with self.assertRaises(ValueError): managed_intake.save(config(self.root), 'holder', self.manager.directory, self.folder)
        file.write_text('[]'); self.manager.reconcile(); self.spawn.assert_not_called()


if __name__ == '__main__': unittest.main(verbosity=2)
