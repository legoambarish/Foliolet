"""Same-byte, local-only baseline/current comparison. All documents are fictional.

Generate the existing corpus with make-ocr-benchmark.py first. Keep the compiled
pre-change classes under .local-data/refresh-baseline-classes. Never reads a vault.
Raw results remain ignored; the summary includes exact-value precision and recall.
"""
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import shutil
import time
import fitz
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--resume', action='store_true', help='Reuse completed same-byte results only with unchanged frozen runtime classes')
parser.add_argument('--after-only', action='store_true', help='Retain the same-byte baseline and rerun the changed implementation')
args = parser.parse_args()

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.local-data/refresh-benchmark'
OUT.mkdir(parents=True, exist_ok=True)
cases = json.loads((ROOT / '.local-data/ocr-p0/cases.json').read_text())


def document(name, lines, expected, scan=False):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((40, 40), 'FICTIONAL EXTRACTION TEST - NO ISSUER AUTHORITY', fontsize=10)
    for i, line in enumerate(lines):
        page.insert_text((40, 80 + i * 24), line, fontsize=11)
    if scan:
        pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5))
        raster = fitz.open()
        p = raster.new_page(width=page.rect.width, height=page.rect.height)
        p.insert_image(p.rect, stream=pix.tobytes('png'))
        doc.close()
        doc = raster
    target = OUT / (name + '.pdf')
    if not ((args.resume or args.after_only) and target.exists()):
        doc.save(target)
    doc.close()
    cases.append(dict(id=name, file=str(target), expected=expected, fictional=True))


invoice = {'Invoice Number': 'INV-00042', 'Customer Number': '0000719', 'Billing Address': '42 Example Lane',
           'Policy Number': 'POL-0024', 'Blood Group': 'O+', 'Account Holder': 'Mira Example',
           'Vehicle Number': 'ZZ00XX0001', 'Order Reference': 'ORD-009', 'Tax Identifier': 'TEST00042',
           'Payment Status': 'PAID', 'Emergency Contact': 'Leela Example', 'Country of Birth': 'India'}
truth = {'extracted.' + k.lower().replace(' ', '_'): v for k, v in invoice.items()}
for scan in (False, True):
    document('broad-fields-' + ('scan' if scan else 'native'), [f'{k}: {v}' for k, v in invoice.items()], truth, scan)
document('distinct-school-labels', ['Previous School: North Valley', 'School: South Valley'],
         {'extracted.previous_school': 'North Valley', 'extracted.school': 'South Valley'})
# Forty-eight fields: no model or OCR needed, and still within the wallet's 64-fact limit.
target = OUT / 'wide-record.txt'
target.write_text(''.join(f'Custom field {i}: value {i}\n' for i in range(1, 49)))
cases.append(dict(id='wide-record', file=str(target), expected={f'extracted.custom_field_{i}': f'value {i}' for i in range(1, 49)}, fictional=True))

deps = (ROOT / '.local-data/refresh.classpath').read_text().strip()
shutil.copytree(ROOT / 'spring-boot-service/target/classes', OUT / 'classes-after', dirs_exist_ok=True)
shutil.copytree(ROOT / 'spring-boot-service/target/test-classes', OUT / 'harness', dirs_exist_ok=True)
def fingerprint(folder):
    h = hashlib.sha256()
    for p in sorted(folder.rglob('*.class')):
        h.update(str(p.relative_to(folder)).encode())
        h.update(p.read_bytes())
    return h.hexdigest()
fingerprints = {v: fingerprint(p) for v,p in [('before', ROOT / '.local-data/refresh-baseline-classes'), ('after', OUT / 'classes-after')]}
fingerprint_file = OUT / 'runtime-fingerprints.json'
if args.resume:
    assert json.loads(fingerprint_file.read_text(encoding='utf-8')) == fingerprints, 'Runtime changed; run a fresh comparison'
elif args.after_only:
    assert json.loads(fingerprint_file.read_text(encoding='utf-8'))['before'] == fingerprints['before']
    previous = OUT / ('intermediate-' + str(time.time_ns()))
    previous.mkdir()
    for p in OUT.glob('*-after.json'):
        shutil.copy2(p, previous / p.name)
    for name in ('metrics.json', 'summary.json', 'runtime-fingerprints.json'):
        if (OUT / name).exists():
            shutil.copy2(OUT / name, previous / name)
    fingerprint_file.write_text(json.dumps(fingerprints), encoding='utf-8')
else:
    fingerprint_file.write_text(json.dumps(fingerprints), encoding='utf-8')
rows = []
for case in cases:
    input_file = ROOT / case['file']
    digest = hashlib.sha256(input_file.read_bytes()).hexdigest()
    for version, classes in [('before', ROOT / '.local-data/refresh-baseline-classes'), ('after', OUT / 'classes-after')]:
        result_file = OUT / f"{case['id']}-{version}.json"
        cp = os.pathsep.join([str(OUT / 'harness'), str(classes), deps])
        started = time.perf_counter()
        print(time.strftime('%H:%M:%S'), 'START', case['id'], version, flush=True)
        reuse = (args.resume or args.after_only and version == 'before') and result_file.exists()
        if not reuse:
            with result_file.with_suffix('.log').open('w') as log:
                process = subprocess.run(['java', '-Xmx512m', '-cp', cp, 'com.sih26190.dms.intake.IntakeBenchmarkMain',
                                          str(input_file), str(result_file)], stdout=log, stderr=log, timeout=240, cwd=ROOT)
            if process.returncode:
                raise RuntimeError(f"Benchmark failed: {case['id']} {version}; see local log")
        data = json.loads(result_file.read_text(encoding='utf-8'))
        assert data['snapshot']['hash'] == digest, 'Cached result belongs to different bytes'
        if data.get('failure'):
            raise RuntimeError(f"Extraction failed: {case['id']} {version}: {data['failure']}")
        fields = data['result']['fields']
        expected = case['expected']
        correct = sum(expected.get(f['path']) == f['value'] for f in fields)
        supported = [f for f in fields if f['support']['quality'] == 'SUPPORTED']
        bindings = 0
        for f in fields:
            text = data['snapshot']['pages'][f['citation']['page'] - 1]['text']
            # OCR may emit Unicode even when the printed fixture is ASCII.
            for part in f['support']['labels'] + f['support']['values'] + f['support']['headers']:
                assert text.encode('utf-16-le')[part['start']*2:part['end']*2].decode('utf-16-le') == part['quote']
                bindings += 1
        row = dict(case=case['id'], version=version, sha256=digest, expected=len(expected), emitted=len(fields), correct=correct,
                   wrong=len(fields)-correct, automaticWrong=sum(expected.get(f['path']) != f['value'] for f in supported),
                   totalMs=data['totalMs'], readingMs=data['readingMs'], modelCalls=data['result']['diagnostics']['modelCalls'],
                   exactSourceFragments=bindings, wallMs=None if reuse else round((time.perf_counter()-started)*1000))
        rows.append(row)
        (OUT/'metrics.json').write_text(json.dumps(rows, indent=2))
        print(time.strftime('%H:%M:%S'), 'DONE', json.dumps(row), flush=True)
summary = {'fictionalOnly': True, 'privateDocumentsSent': 0, 'cases': len(cases), 'rows': rows}
for version in ('before', 'after'):
    subset = [r for r in rows if r['version'] == version]
    correct = sum(r['correct'] for r in subset)
    emitted = sum(r['emitted'] for r in subset)
    expected = sum(r['expected'] for r in subset)
    summary[version] = dict(correct=correct, expected=expected, emitted=emitted, precision=correct/emitted, recall=correct/expected,
                            automaticWrong=sum(r['automaticWrong'] for r in subset),
                            medianMs=statistics.median(r['totalMs'] for r in subset), maximumMs=max(r['totalMs'] for r in subset))
(OUT/'summary.json').write_text(json.dumps(summary, indent=2))
print('COMPLETE', json.dumps({k: v for k, v in summary.items() if k != 'rows'}), flush=True)
