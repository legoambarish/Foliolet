"""Real full-document review and independent 40-clause recall/quote gate."""
import json
import re
import time
from pathlib import Path
import runpy
from foli_corpus import gold_cases

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.local-data/foli'
qa=runpy.run_path(str(ROOT/'tools/test-foli-qa.py'))
fixture=json.loads((OUT/'reading-fixture.json').read_text())
auth,other=fixture['auth']
doc=fixture['documents']['long-contract-125-pages.pdf']
print(time.strftime('%H:%M:%S'),'Starting real full-source review',flush=True)
outcome,seconds=qa['job']({'documentId':doc,'mode':'review','history':[]},auth,other)
assert outcome['state']=='COMPLETE',outcome.get('message')
answer=outcome['result']
normal=lambda text: re.sub(r'\s+',' ',text).strip()
expected=[case for case in gold_cases() if case['id'].startswith('Q')]
hits=[]
for case in expected:
    found=any(case['category'] in finding['categories'] and any(c['page']==case['page'] and normal(case['quote']) in normal(c['quote'])
              for c in finding['citations']) for finding in answer['findings'])
    hits.append({'id':case['id'],'page':case['page'],'category':case['category'],'found':found})
aligned=0
for citation in answer['citations']:
    response=qa['call']('GET','/source',auth,params={'documentId':doc,'hash':citation['sourceHash'],'page':citation['page']})
    response.raise_for_status()
    text=response.json()['page']['text']
    assert text[citation['start']:citation['end']]==citation['quote']
    aligned+=1
flagged_pages={c['page'] for f in answer['findings'] for c in f['citations']}
gold_pages={case['page'] for case in expected}
report={'seconds':seconds,'clauseRecall':sum(h['found'] for h in hits)/len(hits),
        'passagePagePrecision':len(flagged_pages & gold_pages)/max(1,len(flagged_pages)),
        'precisionScope':'Flagged pages versus the authored clause pages, not correctness of AI legal interpretations',
        'quotesAligned':aligned,'gold':hits,'response':answer}
(OUT/'phase-3-live-review.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('Recall',sum(h['found'] for h in hits),'/',len(hits),'quotes aligned',aligned,'seconds',seconds,
      'semantic coverage',answer['reviewCoverage'],flush=True)
assert report['clauseRecall']>=.9
assert answer['manifest']['accountedPages']==125
assert any(c['page']==125 for c in answer['citations'])
