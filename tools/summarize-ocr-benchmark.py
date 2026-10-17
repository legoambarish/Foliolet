"""Publish aggregate metrics only. Real-document transcriptions/values stay private."""
import hashlib
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.local-data/ocr-p0'


def main():
    cases = json.loads((OUT / 'cases.json').read_text())
    report = {'scope': '14 fictional PDFs, 169 explicit golden fields; two private scans without independently labelled truth',
              'definitions': {'recall': 'correct path and entire canonical value / all golden fields',
                              'precision': 'correct path and entire canonical value / emitted fields',
                              'exactValueAccuracy': 'entire correct value / emitted fields whose path has golden truth',
                              'falseSuggestion': 'wrong value, wrong association or no unambiguous golden truth; review suggestions counted separately',
                              'rss': 'sampled peak simultaneous resident benchmark JVM + reader + OCR children; excludes already resident Ollama; 250ms sampling'},
              'phases': {}, 'documents': []}
    rows = {}
    for phase in ('before', 'after'):
        metrics = {r['case']: r for r in json.loads((OUT / phase / 'metrics.json').read_text())}
        totals = dict(golden=0, emitted=0, correct=0, supported=0, correctSupported=0, review=0, correctReview=0, falseSupported=0, falseReview=0, knownPaths=0)
        for case in cases:
            data = json.loads((OUT / phase / (case['id'] + '.json')).read_text())
            fields = (data.get('result') or {}).get('fields', [])
            expected = case['expected']
            score = dict(golden=len(expected), emitted=len(fields), correct=0, supported=0, correctSupported=0, review=0, correctReview=0, falseSupported=0, falseReview=0, knownPaths=0)
            for field in fields:
                correct = field['path'] in expected and field['value'] == expected[field['path']]
                review = (field.get('support') or {}).get('quality') == 'REVIEW_REQUIRED'
                score['correct'] += correct
                score['knownPaths'] += field['path'] in expected
                score['review' if review else 'supported'] += 1
                score['correctReview' if review else 'correctSupported'] += correct
                score['falseReview' if review else 'falseSupported'] += not correct
            for name, value in score.items():
                totals[name] += value
            source_hash = hashlib.sha256((ROOT / case['file']).read_bytes()).hexdigest()
            assert data['snapshot']['hash'] == source_hash, 'Benchmark source bytes changed: ' + case['id']
            rows.setdefault(case['id'], {'case': case['id'], 'sourceSha256': source_hash})[phase] = dict(score, **metrics[case['id']], rejections=(data.get('result') or {}).get('diagnostics', {}).get('rejections', {}))
        totals.update(recall=totals['correct']/totals['golden'], precision=totals['correct']/max(1,totals['emitted']),
                      exactValueAccuracy=totals['correct']/max(1,totals['knownPaths']),
                      supportedPrecision=totals['correctSupported']/max(1,totals['supported']),
                      reviewPrecision=totals['correctReview']/max(1,totals['review']),
                      medianTotalMs=statistics.median(r['totalMs'] for r in metrics.values()),
                      maxTotalMs=max(r['totalMs'] for r in metrics.values()),
                      maxSampledReaderTreeRssBytes=max(r['sampledPeakReaderTreeRssBytes'] for r in metrics.values()))
        report['phases'][phase] = totals
        for name in ('real-01','real-02'):
            data=json.loads((OUT/phase/(name+'.json')).read_text())
            fields=(data.get('result') or {}).get('fields',[])
            source_hash = hashlib.sha256((OUT/'private'/(name+'.pdf')).read_bytes()).hexdigest()
            assert data['snapshot']['hash'] == source_hash, 'Private benchmark source bytes changed'
            rows.setdefault(name, {'case':name,'groundTruth':'Unavailable; no precision or recall claim',
                                  'sourceSha256':source_hash})[phase] = dict(metrics[name], supported=sum((f.get('support') or {}).get('quality')=='SUPPORTED' for f in fields),reviewRequired=sum((f.get('support') or {}).get('quality')=='REVIEW_REQUIRED' for f in fields),rejections=(data.get('result') or {}).get('diagnostics',{}).get('rejections',{}))
    report['documents']=list(rows.values())
    destination=ROOT/'docs/verification/ocr-p0-benchmark.json'
    destination.parent.mkdir(exist_ok=True,parents=True)
    destination.write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report['phases'],indent=2))
    for row in report['documents']:
        print(row['case'],row['before']['fields'],row['after']['fields'])


if __name__ == '__main__':
    main()
