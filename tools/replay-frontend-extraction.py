"""Verify final field-linker changes against every retained benchmark snapshot.

No OCR, model, network, user account, or vault access. The measured OCR comparison
is separate; this replay requires identical final candidates and source bindings.
"""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.local-data/refresh-benchmark'
summary = json.loads((OUT / 'summary.json').read_text(encoding='utf-8'))
cp = os.pathsep.join([str(ROOT / 'spring-boot-service/target/test-classes'),
                      str(ROOT / 'spring-boot-service/target/classes'),
                      (ROOT / '.local-data/refresh.classpath').read_text().strip()])
checks = []
for row in summary['rows']:
    if row['version'] != 'after':
        continue
    source = OUT / (row['case'] + '-after.json')
    output = OUT / (row['case'] + '-final-replay.json')
    with output.with_suffix('.log').open('w') as log:
        subprocess.run(['java', '-Xmx512m', '-cp', cp, 'com.sih26190.dms.intake.IntakeReextractMain', str(source), str(output)],
                       check=True, timeout=30, stdout=log, stderr=log, cwd=ROOT)
    old = json.loads(source.read_text(encoding='utf-8'))['result']
    new = json.loads(output.read_text(encoding='utf-8'))['result']
    assert old['fields'] == new['fields'], row['case']
    assert new['diagnostics']['modelCalls'] == 0, row['case']
    checks.append({'case': row['case'], 'identicalFields': len(new['fields']), 'modelCalls': 0})
    print(time.strftime('%H:%M:%S'), 'PASS', row['case'], flush=True)
(OUT / 'final-replay.json').write_text(json.dumps({'passed': len(checks), 'checks': checks}, indent=2), encoding='utf-8')
