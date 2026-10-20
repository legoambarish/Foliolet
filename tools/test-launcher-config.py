"""Isolated launcher branch/port regressions on Windows PowerShell 5.1 and 7.

No services are started or stopped; each scenario uses a temporary checkout.
"""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = dict(pg=55438, evm=8548, api=8088, ui=8008, receiver=8001, control=8002)
CUSTOM = dict(pg=55448, evm=8558, api=8089, ui=8018, receiver=8101, control=8102)
ENGINES = [str(Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe')]
if shutil.which('pwsh'):
    ENGINES.append(shutil.which('pwsh'))


class LauncherConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='foliolet-launcher-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'tools').mkdir()
        (self.root / '.local-data').mkdir()
        shutil.copy2(ROOT / 'tools/foliolet-desktop-common.ps1', self.root / 'tools')

    def save(self, ports, root=None):
        (self.root / '.local-data/intake-runtime.json').write_text(json.dumps(
            dict(root=root or str(self.root), ports=ports)), encoding='utf8')

    def run_ps(self, engine, code='', branch='codex/askfoli-document-guardrails'):
        script = "$ErrorActionPreference='Stop'\n"
        script += ". '" + str(self.root / 'tools/foliolet-desktop-common.ps1').replace("'", "''") + "'\n"
        script += "function git { $global:LASTEXITCODE=0; '" + branch + "' }\n"
        script += code or "Assert-FolioletBranch; @{ports=$folioletPorts;url=$folioletUrl} | ConvertTo-Json -Compress"
        encoded = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
        return subprocess.run([engine, '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-OutputFormat', 'Text', '-EncodedCommand', encoded],
                              capture_output=True, text=True, timeout=20,
                              creationflags=subprocess.CREATE_NO_WINDOW)

    def test_defaults_and_saved_custom_ports(self):
        for engine in ENGINES:
            for ports in (None, CUSTOM):
                with self.subTest(engine=engine, ports=ports):
                    if ports is None:
                        (self.root / '.local-data/intake-runtime.json').unlink(missing_ok=True)
                    else:
                        self.save(ports)
                    result = self.run_ps(engine)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    output = json.loads(result.stdout)
                    self.assertEqual(output['ports'], ports or DEFAULT)
                    self.assertEqual(output['url'], f"http://127.0.0.1:{(ports or DEFAULT)['ui']}/")

    def test_legacy_runtime_retains_defaults(self):
        self.save(None)
        for engine in ENGINES:
            result = self.run_ps(engine)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['ports'], DEFAULT)

    def test_numeric_port_strings_use_one_canonical_origin(self):
        self.save(dict(CUSTOM, api='08089', ui='08018'))
        for engine in ENGINES:
            result = self.run_ps(engine)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            self.assertEqual(output['ports'], CUSTOM)
            self.assertEqual(output['url'], 'http://127.0.0.1:8018/')

    def test_foreign_workspace_refused(self):
        self.save(CUSTOM, str(self.root / 'other-checkout'))
        for engine in ENGINES:
            result = self.run_ps(engine)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('another checkout', result.stderr)

    def test_invalid_or_duplicate_ports_refused(self):
        for engine in ENGINES:
            for value in (80, 65536, '8089/elsewhere', True, None, CUSTOM['pg']):
                with self.subTest(engine=engine, value=value):
                    self.save(dict(CUSTOM, api=value))
                    result = self.run_ps(engine)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('Runtime ports must be distinct integers', result.stderr)

    def test_main_and_unrelated_branches_remain_refused(self):
        for engine in ENGINES:
            for branch in ('main', 'cf', 'codex/unrelated', 'codex/askfoli-document-guardrails-other'):
                with self.subTest(engine=engine, branch=branch):
                    result = self.run_ps(engine, branch=branch)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('No branch was changed', result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
