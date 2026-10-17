"""Offline fallback boundaries; no private document or installed model is modified."""
import importlib.util
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name('ocr-layout-worker.py')
SPEC = importlib.util.spec_from_file_location('ocr_worker', SCRIPT)
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


class WorkerBoundaries(unittest.TestCase):
    def test_inference_network_attempts_are_denied(self):
        for event in ('socket.connect', 'socket.connect_ex', 'socket.bind', 'socket.getaddrinfo'):
            with self.assertRaises(PermissionError):
                worker.deny_network(event, ())
        worker.deny_network('open', ())

    def test_installed_models_match_pinned_hashes(self):
        root = worker.models()
        self.assertEqual(31_749_509, sum((root / n).stat().st_size for n in worker.MODELS))

    def test_forged_model_is_rejected_without_touching_installed_weights(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'models').mkdir()
            for name in worker.MODELS:
                (root / 'models' / name).write_bytes(b'forged weights')
            with patch.object(worker.importlib.util, 'find_spec', return_value=types.SimpleNamespace(origin=str(root / '__init__.py'))):
                with self.assertRaisesRegex(RuntimeError, 'missing or altered'):
                    worker.models()

    def test_unexpected_package_version_is_rejected(self):
        with patch.object(worker.importlib.metadata, 'version', return_value='0.0.0'):
            with self.assertRaisesRegex(RuntimeError, 'runtime version'):
                worker.models()


if __name__ == '__main__':
    unittest.main(verbosity=2)
