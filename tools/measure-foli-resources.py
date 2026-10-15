"""Measure a real full-review workload on the current local runtime, without authoritative writes."""
import json
from pathlib import Path
import runpy
import subprocess
import threading
import time

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'.local-data/foli'
qa=runpy.run_path(str(ROOT/'tools/test-foli-qa.py')); fixture=json.loads((OUT/'ui-fixture.json').read_text())
samples=[]; finished=threading.Event()
def sample():
    command="@{processes=@(Get-Process -Name ollama,llama-server,java -ErrorAction SilentlyContinue | Select-Object ProcessName,Id,WorkingSet64,PeakWorkingSet64); os=Get-CimInstance Win32_OperatingSystem | Select-Object FreePhysicalMemory,TotalVisibleMemorySize} | ConvertTo-Json -Depth 4 -Compress"
    while not finished.is_set():
        try:
            run=subprocess.run(['powershell.exe','-NoProfile','-Command',command],capture_output=True,text=True,timeout=10,check=True)
            samples.append({'time':time.time(),**json.loads(run.stdout)})
        except Exception as error: samples.append({'unavailable':type(error).__name__})
        finished.wait(.5)
thread=threading.Thread(target=sample,daemon=True); thread.start()
try:
    result,seconds=qa['job']({'mode':'review','documentId':'wallet:'+fixture['documents']['long-contract-125-pages.pdf']['id'],'history':[]},fixture['auth'])
    assert result['state']=='COMPLETE',result.get('code')
finally:
    finished.set(); thread.join(12)
runner=[p for s in samples for p in s.get('processes',[]) if p['ProcessName']=='llama-server']
peak=max(p['PeakWorkingSet64'] for p in runner)
report={'scope':'Fresh runtime, real 125-page full review; samples are process working sets, not total committed memory',
    'seconds':seconds,'coverage':result['result']['reviewCoverage'],'nativeRunnerPeakWorkingSetBytes':peak,'samples':samples,
    'earlierMixedBenchmarkObservation':{'nativeRunnerWorkingSetBytes':9118810112,'nativeRunnerPeakWorkingSetBytes':9119453184,
        'scope':'Manual OS snapshot at 10:02 during the extended model/CPU/application test session; cause not isolated'}}
(OUT/'phase-5-app-resources.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PASS: full review',seconds,'s;',len(samples),'resource samples; native runner peak',round(peak/2**30,3),'GiB')
