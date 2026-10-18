"""End-to-end private jobs/Q&A benchmark on the 80 hand-labeled synthetic cases.

Reuses only the generated reading fixture. Never operates on an existing user's
documents. Respects the production rate limit and records failures honestly.
"""
import argparse
import json
import re
from pathlib import Path
import time
import requests
from foli_corpus import gold_cases

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.local-data/foli'
HTTP=requests.Session()
HTTP.trust_env=False
BASE='http://127.0.0.1:8080/api/foli'
HEADERS={'X-Foli-Client':'private'}


def call(method,path,auth,**kwargs):
    return HTTP.request(method,BASE+path,auth=tuple(auth),headers=HEADERS,timeout=(3,30),**kwargs)


def job(payload,auth,other=None):
    while True:
        response=call('POST','/jobs',auth,json=payload)
        if response.status_code==429:
            print(time.strftime('%H:%M:%S'),'Rate/queue limit: waiting 12 seconds',flush=True)
            time.sleep(12)
            continue
        response.raise_for_status()
        break
    identifier=response.json()['id']
    if other:
        assert call('GET','/jobs/'+identifier,other).status_code==404
        assert call('DELETE','/jobs/'+identifier,other).status_code==404
    start=time.perf_counter()
    while time.perf_counter()-start<310:
        response=call('GET','/jobs/'+identifier,auth)
        response.raise_for_status()
        body=response.json()
        if body['state'] in ('COMPLETE','ERROR','CANCELLED'):
            return body,round(time.perf_counter()-start,3)
        time.sleep(.4)
    raise TimeoutError('private job deadline')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--limit',type=int,default=80)
    parser.add_argument('--output',default='phase-2-qa-live.json')
    parser.add_argument('--ids',nargs='*',help='Optional case IDs for a targeted regression; omitted means the full corpus')
    args=parser.parse_args()
    fixture=json.loads((OUT/'reading-fixture.json').read_text())
    auth,other=fixture['auth']
    doc=fixture['documents']['long-contract-125-pages.pdf']
    results=[]
    health=call('GET','/health',auth).json()
    print('Runtime:',health['ollama']['status'],health['ollama']['model'],flush=True)
    cases=[case for case in gold_cases() if not args.ids or case['id'] in args.ids]
    for case in cases[:args.limit]:
        payload={'question':case['question'],'mode':'chat','history':[]}
        if case['kind']!='general': payload['documentId']=doc
        outcome,seconds=job(payload,auth,other if not results else None)
        answer=outcome.get('result') or {}
        citations=answer.get('citations',[])
        quotes_ok=True
        for citation in citations:
            source=call('GET','/source',auth,params={'documentId':citation['documentId'], 'hash':citation['sourceHash'],'page':citation['page']})
            source.raise_for_status()
            text=source.json()['page']['text']
            quotes_ok &= text[citation['start']:citation['end']]==citation['quote'] and citation['sourceVerified'] is True
        normal=lambda text: re.sub(r'\s+',' ',text).strip()
        supported=any(c['page']==case['page'] and normal(case['quote']) in normal(c['quote']) for c in citations) if case['kind']=='document' else None
        if case['kind']=='unanswerable':
            supported=not citations and any(w in answer.get('answer','').lower() for w in ('not','no ','unable','cannot','missing'))
        if case['kind']=='write': supported=answer.get('answerKind')=='READ_ONLY_EXPLANATION' and not citations
        if case['kind']=='general': supported=answer.get('answerKind')=='DOCUMENT_REQUIRED' and bool(answer.get('answer'))
        item={'id':case['id'],'kind':case['kind'],'seconds':seconds,'state':outcome['state'],
              'goldPage':case['page'],'sourceSupported':supported,'quotationsAligned':quotes_ok,'answer':answer,
              'errorCode':outcome.get('code'),'message':outcome.get('message')}
        results.append(item)
        report={'health':health,'cases':results,'total':len(results),
                'sourceSupportPassed':sum(r['sourceSupported'] is True for r in results),
                'quotationAlignmentFailures':sum(not r['quotationsAligned'] for r in results)}
        (OUT/args.output).write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(time.strftime('%H:%M:%S'),case['id'],outcome['state'],'supported='+str(supported),str(seconds)+'s',flush=True)
    assert all(r['quotationsAligned'] for r in results),'An allegedly verified quote failed exact source alignment'
    assert all(r['sourceSupported'] for r in results if r['kind']=='write'),'Write requests were not safely explained'
    print('Completed',len(results),'real inference/application cases;',report['sourceSupportPassed'],'rubric passes',flush=True)


if __name__=='__main__': main()
