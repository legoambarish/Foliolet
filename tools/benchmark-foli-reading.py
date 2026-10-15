"""Quantify real authorized reader/OCR errors and per-page coverage on synthetic fixtures."""
import json
from pathlib import Path
import re
import time
import uuid
import requests

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'.local-data/foli'
http=requests.Session(); http.trust_env=False
def distance(a,b):
    row=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        next_row=[i]
        for j,y in enumerate(b,1): next_row.append(min(next_row[-1]+1,row[j]+1,row[j-1]+(x!=y)))
        row=next_row
    return row[-1]
def normal(text): return re.sub(r'\s+',' ',text).strip()
def main():
    auth=('foli_ocr_'+uuid.uuid4().hex[:10],uuid.uuid4().hex+'-synthetic')
    r=http.post('http://127.0.0.1:8080/api/auth/register',json={'username':auth[0],'password':auth[1],'role':'HOLDER'},timeout=10); r.raise_for_status()
    gold=normal((OUT/'fixtures/scan-gold.txt').read_text())
    results=[]
    for name in ('scan.pdf','rotated.pdf','mixed.pdf','two-columns.pdf','unreadable.pdf','plain.txt','table.csv'):
        start=time.perf_counter(); data=(OUT/'fixtures'/name).read_bytes()
        r=http.post('http://127.0.0.1:8080/api/wallet/documents',auth=auth,files={'file':(name,data)},data={'displayName':name,'category':'Other'},timeout=30); r.raise_for_status()
        doc='wallet:'+r.json()['id']
        r=http.get('http://127.0.0.1:8080/api/foli/manifest',auth=auth,params={'documentId':doc},timeout=200); r.raise_for_status(); manifest=r.json()
        r=http.get('http://127.0.0.1:8080/api/foli/source',auth=auth,params={'documentId':doc,'hash':manifest['sourceHash'],'page':1},timeout=30); r.raise_for_status(); page=r.json()['page']
        text=normal(page['text']); item={'name':name,'seconds':round(time.perf_counter()-start,3),'manifest':manifest,'page':page}
        assert manifest['totalPages']==manifest['accountedPages']==1
        if name in ('scan.pdf','rotated.pdf'):
            item.update({'characterErrorRate':distance(gold,text)/len(gold),'wordErrorRate':distance(gold.split(),text.split())/len(gold.split())})
            assert '9300' in text and 'unless' in text
        if name=='mixed.pdf': assert '9300' in text and 'overview' in text
        if name=='unreadable.pdf': assert not manifest['complete'] and not text
        if name=='two-columns.pdf':
            assert 'Left column' in text and 'Right column' in text
            assert any('reading order' in warning for warning in page['warnings'])
        results.append(item); print(time.strftime('%H:%M:%S'),name,page['status'],item['seconds'],'s',item.get('characterErrorRate',''),flush=True)
        (OUT/'phase-5-reader-benchmark.json').write_text(json.dumps({'scope':'Seven synthetic fixture files; whitespace normalized only for OCR gold comparison','results':results},indent=2),encoding='utf-8')
    print('PASS: all seven reader fixtures accounted for with explicit uncertainty',flush=True)
if __name__=='__main__': main()
