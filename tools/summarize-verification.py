"""Derive final counts and build hashes from executed test artifacts, never invented totals."""
import ast, hashlib, json, pathlib, re, subprocess, xml.etree.ElementTree as ET
root = pathlib.Path(__file__).resolve().parents[1]
artifacts = root / '.bridge-data/artifacts'
def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()
def artifact(name):
    return json.loads((artifacts / name).read_text(encoding='utf-8-sig'))
suites = [ET.parse(p).getroot() for p in (root / 'spring-boot-service/target/surefire-reports').glob('TEST-*.xml')]
java = {key: sum(int(s.get(key, '0')) for s in suites) for key in ['tests','failures','errors','skipped']}
java['suite_count'] = len(suites)
node_log = (artifacts / 'node-tests.log').read_text()
node = {key: int(re.search(r'\b'+key+r' (\d+)', node_log).group(1)) for key in ['tests','pass','fail','skipped']}
django_log = (artifacts / 'django-tests.log').read_text()
django = {'tests': int(re.search(r'Ran (\d+) tests', django_log).group(1)), 'passed': '\nOK\n' in django_log}
report = {'java': java, 'node': node, 'django': django}
for key, name in [('live','live-results.json'),('workflows','workflow-results.json'),('recovery','recovery-results.json'),('offline','offline-results.json'),('ui','ui/ui-results.json')]:
    data = artifact(name)
    report[key] = {k:v for k,v in data.items() if k in {'passed','checks','assertions','pageErrors','browser','viewports','at','planner','simulation','historical','current','chainUnavailable','appPortsClosed','readerReachable','chainReachable','readBlock'}}
ai = artifact('spring-ai-results.json')
report['spring_ai'] = {'passed': ai['passed'], 'checks': ai['checks'], 'seconds': ai['seconds'], 'status': ai['response']['status'], 'modelUsed': ai['response']['modelUsed']}
report['contract_reproducibility'] = artifact('contract-reproducibility.json')['passed']
report['npm_audit'] = artifact('npm-audit-final.json')['metadata']['vulnerabilities']
report['secrets'] = ast.literal_eval((artifacts/'secret-scan.log').read_text().strip())
report['jar_sha256'] = digest(root / 'spring-boot-service/target/dms-0.0.1-SNAPSHOT.jar')
report['evidence_sha256'] = {str(p.relative_to(root)).replace('\\','/'):digest(p) for p in [artifacts/'node-tests.log',artifacts/'django-tests.log',artifacts/'rehearsal.log',artifacts/'browser-rehearsal.log',artifacts/'offline-results.json',artifacts/'recovery-results.json',artifacts/'spring-ai-results.json']}
report['branch'] = subprocess.check_output(['git','branch','--show-current'], cwd=root).decode().strip()
report['main_ref'] = subprocess.check_output(['git','rev-parse','main'], cwd=root).decode().strip()
report['docker_runtime'] = 'UNVERIFIED: engine stale socket; automatic approval review rejected removal'
(root / 'docs/verification-results.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
summary = f'''<!-- MACHINE_RESULTS -->
| Executed check | Actual result |
| --- | --- |
| Maven | {java['tests']} tests, {java['failures']} failures, {java['errors']} errors |
| Node verifier, canonical vectors and governed real-EVM suite | {node['pass']}/{node['tests']} pass |
| Django including restricted public routing | {django['tests']} tests, passed={django['passed']} |
| Primary live workflow | {report['live']['checks']} checks, passed={report['live']['passed']} |
| Approval/import/secondary live workflow | {report['workflows']['checks']} checks, passed={report['workflows']['passed']} |
| Issuance persistence-gap simulation | {report['recovery']['checks']} checks, passed={report['recovery']['passed']} |
| Browser rehearsal | {report['ui']['assertions']} assertions, {len(report['ui']['pageErrors'])} page errors |
| Spring grounded boundary | {report['spring_ai']['status']}, modelUsed={report['spring_ai']['modelUsed']}, {report['spring_ai']['seconds']} seconds |
| App/AI stopped, direct RPC reader | Historical {report['offline']['historical']}; current {report['offline']['current']} |
| RPC stopped | Current {report['offline']['chainUnavailable']} |
| Fresh contract ABI/bytecode compile | Matching hashes: {report['contract_reproducibility']} |
| Narrow source secret scan | {report['secrets']['files_scanned']} files; {len(report['secrets']['suspected_secret_locations'])} suspected matches |
| Npm development dependency audit | {report['npm_audit']['total']} findings, including {report['npm_audit']['critical']} critical and {report['npm_audit']['high']} high |

Packaged jar SHA-256: `{report['jar_sha256']}`. Test evidence hashes and detailed counters are in [verification-results.json](verification-results.json).
<!-- END_MACHINE_RESULTS -->'''
verification = root / 'docs/FINAL_VERIFICATION.md'
content = verification.read_text(encoding='utf-8')
content = re.sub(r'<!-- MACHINE_RESULTS -->.*?<!-- END_MACHINE_RESULTS -->', lambda _:summary, content, flags=re.S)
verification.write_text(content, encoding='utf-8')
print(json.dumps(report, indent=2))
