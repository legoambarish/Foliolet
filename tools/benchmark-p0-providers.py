"""Only fixed fictional/public-knowledge cases may enter this cloud benchmark.

No source-file argument. Key is read from the server process environment and never logged.
Provider timings are not substituted for application/browser end-to-end timings.
"""
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import statistics
import time
import urllib.request
import urllib.error

spec = importlib.util.spec_from_file_location('rubric', Path(__file__).with_name('benchmark-foli-models.py'))
rubric = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rubric)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--provider',choices=['gemini','ollama'],required=True)
    ap.add_argument('--model',required=True);ap.add_argument('--output',required=True);args=ap.parse_args()
    if args.provider=='gemini' and args.model not in ['gemini-3.5-flash-lite','gemini-3.8-flash']:
        raise SystemExit('Only reviewed benchmark models are allowed')
    key=os.environ.get('GEMINI_API_KEY','')
    if args.provider=='gemini' and not key:raise SystemExit('GEMINI_API_KEY missing; no request sent')
    http=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    rows=[];output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    for case in rubric.CASES:
        start=time.monotonic();first=None;text='';usage={};row={'case':case[0]}
        print(time.strftime('%H:%M:%S'),'START',args.model,case[0],flush=True)
        prompt='Fictional source: '+case[1]+'\nQuestion: '+case[2]
        if args.provider=='gemini':
            url='https://generativelanguage.googleapis.com/v1beta/models/'+args.model+':streamGenerateContent?alt=sse'
            body={'systemInstruction':{'parts':[{'text':rubric.SYSTEM}]},'contents':[{'parts':[{'text':prompt}]}],
                  'generationConfig':{'temperature':0.1,'maxOutputTokens':900,'responseMimeType':'application/json'}}
            headers={'Content-Type':'application/json','x-goog-api-key':key}
        else:
            url='http://127.0.0.1:11444/api/chat'
            body={'model':args.model,'messages':[{'role':'system','content':rubric.SYSTEM},{'role':'user','content':prompt}],
                  'format':'json','think':False,'stream':True,'options':{'temperature':0.1,'num_ctx':8192,'num_predict':900},'keep_alive':'10m'}
            headers={'Content-Type':'application/json'}
        try:
            req=urllib.request.Request(url,data=json.dumps(body).encode(),headers=headers)
            with http.open(req,timeout=120) as response:
                consumed=0
                for raw in response:
                    consumed+=len(raw)
                    if consumed>150000:raise ValueError('Response limit')
                    if args.provider=='gemini':
                        if not raw.startswith(b'data: '):continue
                        part=json.loads(raw[6:]);chunks=part.get('candidates',[{}])[0].get('content',{}).get('parts',[])
                        added=''.join(c.get('text','') for c in chunks if not c.get('thought'))
                        usage=part.get('usageMetadata',usage)
                    else:
                        part=json.loads(raw);added=part.get('message',{}).get('content','')
                        if part.get('done'):usage={k:part[k] for k in ['load_duration','prompt_eval_duration','eval_duration','prompt_eval_count','eval_count','total_duration'] if k in part}
                    if added and first is None:first=round((time.monotonic()-start)*1000,2)
                    text+=added
            row.update(rubric.score(case,{'message':{'content':text}}));row['usage']=usage
        except urllib.error.HTTPError as error:row.update({'pass':False,'httpStatus':error.code})
        except Exception as error:row.update({'pass':False,'failure':type(error).__name__})
        row.update({'totalMs':round((time.monotonic()-start)*1000,2),'firstTokenMs':first});rows.append(row)
        times=sorted(r['totalMs'] for r in rows if 'usage' in r)
        report={'provider':args.provider,'model':args.model,'fictionalOnly':True,'billingTier':'UNVERIFIED' if args.provider=='gemini' else 'LOCAL',
                'scope':'Provider-only fixed rubric; first token is not a validated answer; provider cold state uncontrolled',
                'cases':rows,'passed':sum(r['pass'] for r in rows),'total':len(rows),
                'p50Ms':statistics.median(times) if times else None,'p95Ms':times[math.ceil(len(times)*.95)-1] if times else None}
        output.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(time.strftime('%H:%M:%S'),'DONE',case[0],row['totalMs'],'ms',row['pass'],flush=True)

if __name__=='__main__':main()
