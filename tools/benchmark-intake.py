"""Run identical local documents against a saved/current Java pipeline; never print their contents."""
import argparse,ctypes,json,os,subprocess,time
from ctypes import wintypes as w
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'.local-data/ocr-p0'

def memory_tree(pid):
    """Sample simultaneous RSS of the benchmark JVM and its reader/Tesseract children on Windows."""
    if os.name!='nt':return 0
    class Entry(ctypes.Structure):
        _fields_=[('size',w.DWORD),('usage',w.DWORD),('pid',w.DWORD),('heap',ctypes.c_size_t),('module',w.DWORD),('threads',w.DWORD),('parent',w.DWORD),('priority',w.LONG),('flags',w.DWORD),('exe',w.WCHAR*260)]
    class Counters(ctypes.Structure):
        _fields_=[('cb',w.DWORD),('faults',w.DWORD)]+[(n,ctypes.c_size_t) for n in ('peak','rss','peakPaged','paged','peakNonPaged','nonPaged','pagefile','peakPagefile','private')]
    k=ctypes.WinDLL('kernel32',use_last_error=True);ps=ctypes.WinDLL('psapi',use_last_error=True)
    k.CreateToolhelp32Snapshot.restype=w.HANDLE;k.OpenProcess.restype=w.HANDLE
    k.CloseHandle.argtypes=[w.HANDLE];k.Process32FirstW.argtypes=[w.HANDLE,ctypes.POINTER(Entry)];k.Process32NextW.argtypes=k.Process32FirstW.argtypes
    ps.GetProcessMemoryInfo.argtypes=[w.HANDLE,ctypes.POINTER(Counters),w.DWORD]
    handle=k.CreateToolhelp32Snapshot(2,0);entry=Entry();entry.size=ctypes.sizeof(entry);parents={}
    try:
        ok=k.Process32FirstW(handle,ctypes.byref(entry))
        while ok:parents[entry.pid]=entry.parent;ok=k.Process32NextW(handle,ctypes.byref(entry))
    finally:k.CloseHandle(handle)
    pids={pid}
    while True:
        more={p for p,parent in parents.items() if parent in pids};n=len(pids);pids.update(more)
        if len(pids)==n:break
    total=0
    for p in pids:
        h=k.OpenProcess(0x410,False,p)
        if not h:continue
        try:
            c=Counters();c.cb=ctypes.sizeof(c)
            if ps.GetProcessMemoryInfo(h,ctypes.byref(c),c.cb):total+=c.rss
        finally:k.CloseHandle(h)
    return total

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--phase',required=True);ap.add_argument('--only');a=ap.parse_args()
    cpfile=OUT/'baseline.classpath' if a.phase=='before' else ROOT/'spring-boot-service/target/ocr-benchmark.classpath'
    cp=cpfile.read_text().strip()
    if a.phase!='before':cp=str(ROOT/'spring-boot-service/target/test-classes')+';'+str(ROOT/'spring-boot-service/target/classes')+';'+cp
    cases=json.loads((OUT/'cases.json').read_text())
    for sample in json.loads((OUT/'private/inventory.json').read_text()):cases.append({'id':sample['file'][:-4],'file':str(OUT/'private'/sample['file']),'fictional':False,'expected':{}})
    results=[];dest=OUT/a.phase;dest.mkdir(exist_ok=True)
    env=dict(os.environ,FOLI_TESSERACT=str(ROOT.parent/'Foliolet-testcloudflare/.local-tools/ocr/Library/bin/tesseract.exe'),
             FOLI_OCR_DATA_DIR=str(ROOT.parent/'Foliolet-testcloudflare/.local-tools/ocr/share/tessdata'),FOLI_OLLAMA_URL='http://127.0.0.1:11444',
             FOLI_LAYOUT_PYTHON=str(ROOT/'.venv/Scripts/python.exe'),FOLI_LAYOUT_SCRIPT=str(ROOT/'tools/ocr-layout-worker.py'))
    for case in cases:
        if a.only and case['id'] not in a.only.split(','):continue
        target=dest/(case['id']+'.json');start=time.monotonic();peak=0;notice=0
        print(time.strftime('%H:%M:%S'),'START',a.phase,case['id'],flush=True)
        with (dest/(case['id']+'.log')).open('w',encoding='utf8') as log:
            p=subprocess.Popen(['java','-Xmx512m','-cp',cp,'com.sih26190.dms.intake.IntakeBenchmarkMain',str(ROOT/case['file']),str(target)],env=env,stdout=log,stderr=log)
            while p.poll() is None:
                peak=max(peak,memory_tree(p.pid));elapsed=time.monotonic()-start
                if elapsed>notice+15:print(time.strftime('%H:%M:%S'),'ACTIVE',case['id'],round(elapsed),'seconds',flush=True);notice=elapsed
                if elapsed>390:p.kill();raise RuntimeError('Benchmark worker exceeded bounded budget: '+case['id'])
                time.sleep(.25)
        if p.returncode:raise RuntimeError('Benchmark failed; inspect private log: '+case['id'])
        data=json.loads(target.read_text());fields=(data.get('result') or {}).get('fields',[])
        record={'case':case['id'],'fictional':case['fictional'],'fields':len(fields),'readingMs':data['readingMs'],'totalMs':data['totalMs'],
                'sampledPeakReaderTreeRssBytes':peak,'failure':data.get('failure'),'matchedTargets':sum(any(f['path']==path and f['value']==value for f in fields) for path,value in case['expected'].items()),'targetCount':len(case['expected'])}
        results.append(record);(dest/'metrics.json').write_text(json.dumps(results,indent=2),encoding='utf8')
        print(time.strftime('%H:%M:%S'),'DONE',case['id'],'fields='+str(len(fields)),'ms='+str(data['totalMs']),flush=True)
    print('COMPLETE',a.phase,len(results),'cases',flush=True)
if __name__=='__main__':main()
