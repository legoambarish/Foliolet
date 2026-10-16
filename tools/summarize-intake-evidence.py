"""Export only passing test names/counts; never publish private checkpoints or logs."""
import json
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / '.local-data'
BASE = 'b053b324e87d4a90f4d0151d3f7e7077759a89c5'
MAIN = 'c04741ee68563566dc82ab4e71b97c3898714f72'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def main():
    assert git('branch', '--show-current') == 'feature/digilocker-assisted-intake'
    assert git('rev-parse', 'cf') == BASE and git('rev-parse', 'origin/cf') == BASE
    assert git('rev-parse', 'main') == MAIN
    assert git('merge-base', 'HEAD', 'cf') == BASE
    java = []
    for path in sorted((ROOT / 'spring-boot-service/target/surefire-reports').glob('TEST-*.xml')):
        suite = ET.parse(path).getroot()
        entry = {'name': suite.get('name'), **{key: int(suite.get(key, '0')) for key in ('tests', 'failures', 'errors', 'skipped')}}
        assert entry['failures'] == entry['errors'] == entry['skipped'] == 0
        java.append(entry)
    assert sum(s['tests'] for s in java) == 100
    counts = {}
    for name, filename, expected in [('django', 'intake-django-final.log', 72), ('watcher', 'intake-watcher-tests.log', 11)]:
        log = (DATA / filename).read_text(encoding='utf8')
        assert re.search(r'(?m)^OK$', log)
        count = int(re.search(r'Ran (\d+) tests', log)[1]); assert count == expected
        counts[name] = {'result': 'PASS', 'count': count, 'log': '.local-data/' + filename}
    node = (DATA / 'intake-node-verifier.log').read_text(encoding='utf8')
    assert re.search(r'(?m)^.*pass 22$', node) and re.search(r'(?m)^.*fail 0$', node)
    counts['nodeVerifier'] = {'result': 'PASS', 'count': 22, 'log': '.local-data/intake-node-verifier.log'}
    assert 'PASS: registry authorization' in (DATA / 'intake-node-contracts.log').read_text(encoding='utf8')
    counts['contracts'] = {'result': 'PASS', 'merkleShapes': 7, 'log': '.local-data/intake-node-contracts.log'}
    for name, expected in [('live', 46), ('ui', 11), ('failure', 12), ('launcher', 3), ('format', 3)]:
        raw = json.loads((DATA / 'intake-tests' / (name + '-results.json')).read_text(encoding='utf8'))
        assert raw['count'] == expected
        checks = [{'name': c['name'], 'result': c['result']} for c in raw.get('checks', [])]
        assert all(c['result'] == 'PASS' for c in checks)
        assert checks or raw.get('result') == 'PASS'
        counts[name] = {'result': 'PASS', 'count': expected, 'checks': checks}
    output = {'generatedAt': datetime.now(timezone.utc).isoformat(), 'sourceCommit': git('rev-parse', 'HEAD'),
              'branch': git('branch', '--show-current'), 'base': BASE, 'mainPreserved': MAIN,
              'syntheticDocumentsOnly': True, 'realDigiLockerAuthentication': 'NOT TESTED',
              'realIssuedDocument': 'NOT TESTED', 'physicalNfc': 'NOT TESTED',
              'issuerCryptographicVerification': 'NOT IMPLEMENTED', 'java': {'result': 'PASS', 'count': 100, 'suites': java},
              'gates': counts, 'pythonEnvironment': (DATA / 'intake-python-packages.txt').read_text(encoding='utf8').splitlines()}
    path = ROOT / 'docs/intake-demo/evidence.json'; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2) + '\n', encoding='utf8')
    print('PASS Exported sanitized counts and test names; private configs, source QR payloads and logs excluded.')


if __name__ == '__main__': main()
