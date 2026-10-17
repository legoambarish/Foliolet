"""Compare retained baseline classes with current intake using fictional fixtures only.

Run make-intake-fixtures.py first, retain baseline target/classes before building,
then pass --baseline-classes. Uses installed local OCR/model configuration only.
Raw source reports remain under ignored .local-data; summary contains metrics only.
"""
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import time
import psutil

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--baseline-classes', type=Path, required=True)
parser.add_argument('--runs', type=int, default=3)
parser.add_argument('--cases', nargs='+', default=['neither.pdf','table.pdf','scanned.pdf','both.pdf'])
args = parser.parse_args()
target = ROOT / 'spring-boot-service/target'
out = ROOT / '.local-data/p0/intake-benchmark'
out.mkdir(parents=True, exist_ok=True)
dependencies = (target/'p0.classpath').read_text().strip()
records = []
for name in args.cases:
    if Path(name).name != name: raise ValueError('Use a fixture filename, not a path')
    for version, classes in [('before', args.baseline_classes), ('after', target/'classes')]:
        for run in range(args.runs):
            result = out / f'{version}-{name}-{run}.json'
            cp = os.pathsep.join([str(target/'test-classes'), str(classes.resolve()), dependencies])
            start, peak = time.perf_counter(), 0
            with result.with_suffix('.log').open('w') as log:
                process = subprocess.Popen(['java', '-Xmx512m', '-cp', cp,
                    'com.sih26190.dms.intake.IntakeBenchmarkMain',
                    str(ROOT/'.local-data/intake-tests/fixtures'/name), str(result)], stdout=log, stderr=log)
                while process.poll() is None:
                    try:
                        root = psutil.Process(process.pid)
                        peak = max(peak, sum(p.memory_info().rss for p in [root]+root.children(recursive=True)))
                    except psutil.Error:
                        pass
                    if time.perf_counter()-start > 310:
                        raise TimeoutError('Bounded intake subprocess exceeded its deadline')
                    time.sleep(.2)
            assert process.returncode == 0, result.name
            data = json.loads(result.read_text())
            fields = (data.get('result') or {}).get('fields', [])
            row = dict(case=name, version=version, run=run, totalMs=data['totalMs'],
                readingMs=data['readingMs'], wallMs=round((time.perf_counter()-start)*1000),
                sampledPeakTreeRssMiB=round(peak/1048576, 1), failure=data.get('failure'),
                emitted=len(fields), math90=any(f.get('path') == 'education.math' and f.get('value') == '90' for f in fields),
                citations=sum(bool(f.get('citation')) for f in fields),
                modelCalls=(data.get('result') or {}).get('diagnostics',{}).get('modelCalls'),
                indicators=data.get('indicators', {}).get('status'))
            records.append(row)
            (out/'metrics.json').write_text(json.dumps(records, indent=2))
            print(json.dumps(row), flush=True)
print('Completed fictional extraction comparison; cold JVM per trial, shared warm local model; no cloud calls.')
