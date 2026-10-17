"""Run the actual Java intake pipeline on explicitly supplied non-private cases.

Requires psutil. No hidden private inventory, sibling worktree or cloud model access.
RSS is the sampled simultaneous process-tree resident set, not peak JVM heap.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import statistics
import subprocess
import time
import psutil


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rss(pid):
    try:
        root = psutil.Process(pid)
        processes = [root] + root.children(recursive=True)
    except psutil.Error:
        return 0
    total = 0
    for process in processes:
        try: total += process.memory_info().rss
        except psutil.Error: pass
    return total


def stop_tree(process):
    try: children = psutil.Process(process.pid).children(recursive=True)
    except psutil.Error: children = []
    if os.name != 'nt':
        try: os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError: pass
    for child in children:
        try: child.kill()
        except psutil.Error: pass
    process.kill()
    process.wait(timeout=10)


def score(case, data):
    fields = (data.get('result') or {}).get('fields', [])
    expected = case.get('expected', {})
    matches = set()
    counts = dict(golden=len(expected), emitted=len(fields), correct=0, review=0,
                  falseAutomatic=0, falseReview=0, sourceSpanValid=0, sourceSpanTotal=0)
    pages = {p['number']: p for p in (data.get('snapshot') or {}).get('pages', [])}
    for field in fields:
        pair = (field.get('path'), field.get('value'))
        correct = pair[0] in expected and pair[1] == expected[pair[0]]
        if correct: matches.add(pair)
        counts['correct'] += int(correct)
        review = (field.get('support') or {}).get('quality') == 'REVIEW_REQUIRED'
        counts['review'] += int(review)
        if not correct: counts['falseReview' if review else 'falseAutomatic'] += 1
        citation = field.get('citation') or {}
        page = pages.get(citation.get('page'), {})
        text = page.get('text', '')
        support = field.get('support') or {}
        for group in ('labels', 'values', 'headers'):
            for fragment in support.get(group, []):
                counts['sourceSpanTotal'] += 1
                start, end = fragment.get('start', -1), fragment.get('end', -1)
                # Java uses UTF-16 offsets; convert Python text before exact comparison.
                units = text.encode('utf-16-le')
                quote = units[start * 2:end * 2].decode('utf-16-le', errors='replace') if 0 <= start < end <= len(units)//2 else None
                counts['sourceSpanValid'] += int(quote == fragment.get('quote'))
    counts['uniqueCorrect'] = len(matches)
    counts['recall'] = len(matches) / len(expected) if expected else None
    counts['precision'] = counts['correct'] / len(fields) if fields and expected else None
    if not expected:
        # Unlabelled/OOD outputs are not false merely because their schema differs.
        for key in ('correct', 'uniqueCorrect', 'falseAutomatic', 'falseReview'): counts[key] = None
    return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--case-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    source = args.source.resolve()
    target = source / 'spring-boot-service/target'
    cp = os.pathsep.join([str(target/'test-classes'), str(target/'classes'),
                         (target/'ocr-benchmark.classpath').read_text().strip()])
    cases = json.loads(args.cases.read_text())
    if any(not c.get('fictional') and c.get('license') != 'CC-BY-4.0' for c in cases):
        raise ValueError('Only explicitly fictional or approved CC-BY-4.0 public cases are accepted')
    args.out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, FOLI_OLLAMA_URL='http://127.0.0.1:11444')
    records = []
    for case in cases:
        identifier = case['id']
        if not identifier.replace('-', '').replace('_', '').isalnum(): raise ValueError('Invalid case id')
        path = (args.case_root/case['file']).resolve()
        path.relative_to(args.case_root.resolve())
        output = args.out/(identifier+'.json')
        started, peak = time.monotonic(), 0
        with (args.out/(identifier+'.log')).open('w') as log:
            process = subprocess.Popen(['java', '-Xmx512m', '-cp', cp,
                'com.sih26190.dms.intake.IntakeBenchmarkMain', str(path), str(output)],
                env=env, stdout=log, stderr=log, start_new_session=os.name != 'nt')
            timed_out = False
            while process.poll() is None:
                peak = max(peak, rss(process.pid))
                if time.monotonic()-started > args.timeout:
                    stop_tree(process); timed_out = True; break
                time.sleep(.25)
        data = json.loads(output.read_text()) if output.is_file() else {}
        record = dict(case=identifier, category=case.get('category','synthetic'), split=case.get('split','fixture'),
            sourceSha256=digest(path), wallSeconds=time.monotonic()-started, sampledPeakTreeRssBytes=peak,
            exitCode=process.returncode, timedOut=timed_out, readingMs=data.get('readingMs'),
            totalMs=data.get('totalMs'), pipelineFailure=data.get('failure'), **score(case,data))
        if data and (data.get('snapshot') or {}).get('hash') != record['sourceSha256']:
            raise AssertionError('Source bytes and reader hash differ: '+identifier)
        records.append(record)
        (args.out/'metrics.json').write_text(json.dumps(records,indent=2))
        print(json.dumps(record), flush=True)
    labelled = [r for r in records if r['golden']]
    summary = dict(cases=len(records), labelledCases=len(labelled), golden=sum(r['golden'] for r in labelled),
        emitted=sum(r['emitted'] for r in labelled), correct=sum(r['correct'] for r in labelled),
        uniqueCorrect=sum(r['uniqueCorrect'] for r in labelled),
        falseAutomatic=sum(r['falseAutomatic'] for r in labelled), falseReview=sum(r['falseReview'] for r in labelled),
        sourceSpanValid=sum(r['sourceSpanValid'] for r in records), sourceSpanTotal=sum(r['sourceSpanTotal'] for r in records),
        medianWallSeconds=statistics.median(r['wallSeconds'] for r in records),
        maxWallSeconds=max(r['wallSeconds'] for r in records),
        maxSampledTreeRssBytes=max(r['sampledPeakTreeRssBytes'] for r in records),
        failures=sum(r['exitCode'] != 0 or r['timedOut'] or bool(r['pipelineFailure']) for r in records),
        caveat='250 ms process-tree RSS sampling; cold process per document; absent local LLM; not universal accuracy')
    summary['recall'] = summary['uniqueCorrect']/summary['golden'] if summary['golden'] else None
    summary['precision'] = summary['correct']/summary['emitted'] if summary['emitted'] else None
    (args.out/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))

if __name__ == '__main__': main()
