"""Explicit fault simulation against the isolated native demo database, never legacy data."""
import argparse, json, pathlib, time
import psycopg, requests

parser = argparse.ArgumentParser()
parser.add_argument('--simulate-persistence-gap', action='store_true')
args = parser.parse_args()
if not args.simulate_persistence_gap:
    raise SystemExit('Use --simulate-persistence-gap to authorize this isolated test fixture.')
root = pathlib.Path(__file__).resolve().parents[1]
pins = json.loads((root / '.bridge-data/config/bridge-pins.json').read_text())
password = 'Foliolet-Demo-2026!'
issuer = requests.Session()
issuer.auth = ('university', password)
base = 'http://127.0.0.1:8080'

def api(route, body):
    response = issuer.post(base + '/api/bridge/' + route, json=body, timeout=40)
    response.raise_for_status()
    return response.json()

# Reuse a holder whose key was established by the preceding live rehearsal.
holder = json.loads((root / '.bridge-data/artifacts/live-results.json').read_text())['holder']
source = issuer.post(base + '/api/wallet/documents', files={'file': ('recovery.txt', b'CGPA: 8.7\nEnrolled: true\n')}, data={'displayName': 'Recovery fixture', 'category': 'Education'}, timeout=15)
source.raise_for_status()
body = {'claimType': 'internship-eligibility/v1', 'holder': holder, 'sourceDocumentId': source.json()['id'], 'values': {'subject.name': 'Recovery Fixture', 'education.cgpa': '8.7', 'education.enrolled': 'true'}, 'expiresAt': int(time.time()) + 86400}
first = api('issue', body)
repeated = api('issue', body)
assert first['id'] == repeated['id'], 'Exact issuance retry must retain the immutable identity'
with psycopg.connect('host=127.0.0.1 port=55433 user=foliolet dbname=foliolet_bridge') as connection:
    changed = connection.execute("UPDATE bridge_items SET status='ANCHOR_PENDING', revision=revision+1 WHERE id=%s AND owner='university' AND kind='CREDENTIAL' AND status='ACTIVE'", (first['id'],)).rowcount
    assert changed == 1
recovered = api('credentials/' + first['id'] + '/retry', {})
assert recovered['id'] == first['id'] and recovered['status'] == 'ACTIVE'
assert recovered['credential'] == first['credential'], 'Reconciliation may not replace commitments'
report = {'passed': True, 'checks': 3, 'simulation': 'Committed chain record with pending database lifecycle, not a real process crash', 'credentialId': first['id'], 'at': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
(root / '.bridge-data/artifacts/recovery-results.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
