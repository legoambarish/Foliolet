"""Verify the bounded reader entry point with the real packaged Boot JAR."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
jar=root/'spring-boot-service/target/dms-0.0.1-SNAPSHOT.jar'
data=b'Packaged reader: no renewal fee unless notice is late.'
request={'source':{'document':{'id':'wallet:0x'+'a'*64,'name':'Synthetic','filename':'synthetic.txt',
    'format':'txt','status':'DRAFT','version':'1','supported':True},'hash':hashlib.sha256(data).hexdigest(),
    'bytes':base64.b64encode(data).decode()},'config':{'tempDir':str(root/'.local-data/foli/tmp')},'mode':'extract','page':0}
run=subprocess.run(['java','-Xmx512m','-Dloader.main=com.sih26190.dms.foli.FoliReaderMain','-cp',str(jar),
    'org.springframework.boot.loader.launch.PropertiesLauncher'],input=json.dumps(request),text=True,capture_output=True,timeout=30)
assert run.returncode==0,run.stderr[:500]
result=json.loads(next(line.split('\t',1)[1] for line in run.stdout.splitlines() if line.startswith('FOLI_RESULT\t')))
assert result['snapshot']['pages'][0]['text']==data.decode()
print('PASS: real packaged Boot JAR reader preserves the exact synthetic source')
