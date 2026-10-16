"""Run the real Bash launcher against an inert Docker double on macOS/Linux."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
DOCKER='''#!/usr/bin/env python3
import json,os,sys
args=sys.argv[1:]
with open(os.environ['FAKE_DOCKER_LOG'],'a') as log: log.write(json.dumps(args)+'\\n')
if args[:2]==['context','inspect']: print('unix:///var/run/docker.sock')
if args and args[0]=='compose' and 'version' not in args and os.environ.get('FAKE_DOCKER_FAIL')=='1': sys.exit(17)
'''

@unittest.skipIf(os.name=='nt', 'Bash launcher lifecycle runs on both hosted Mac architectures and Linux')
class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path.home())
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        binary=self.root/'docker';binary.write_text(DOCKER);binary.chmod(0o700)
        self.log=self.root/'calls.jsonl'
        self.env=dict(os.environ, PATH=str(self.root)+os.pathsep+os.environ['PATH'],
                      FAKE_DOCKER_LOG=str(self.log), FOLIOLET_INTAKE_DIR=str(self.root/'dedicated inbox'),
                      FOLIOLET_NO_OPEN='1', FOLIOLET_SKIP_BUILD='1')
        self.env.pop('DOCKER_HOST',None)
    def run_launcher(self,*args):
        return subprocess.run(['bash',str(ROOT/'foliolet'),*args],env=self.env,capture_output=True,text=True)
    def calls(self): return [json.loads(x) for x in self.log.read_text().splitlines()]
    def test_one_command_sets_up_folder_and_waits_for_all_services(self):
        result=self.run_launcher('up')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(Path(self.env['FOLIOLET_INTAKE_DIR']).is_dir())
        self.assertTrue(any('--wait' in c and '--no-build' in c for c in self.calls()))
        self.assertIn('http://127.0.0.1:8008',result.stdout)
    def test_down_retains_all_volumes(self):
        result=self.run_launcher('down');self.assertEqual(result.returncode,0,result.stderr)
        actual=self.calls()[-1]
        self.assertEqual(actual[-1],'down');self.assertNotIn('-v',actual);self.assertNotIn('--volumes',actual)
    def test_remote_docker_context_is_rejected(self):
        self.env['DOCKER_HOST']='tcp://example.com:2376'
        self.assertNotEqual(self.run_launcher('up').returncode,0)
        self.assertFalse(Path(self.env['FOLIOLET_INTAKE_DIR']).exists())
    def test_symlink_and_broad_personal_folder_are_rejected(self):
        link=self.root/'link';link.symlink_to(self.root,target_is_directory=True)
        for folder in (str(Path.home()),str(link/'child')):
            self.env['FOLIOLET_INTAKE_DIR']=folder
            self.assertNotEqual(self.run_launcher('up').returncode,0)
    def test_failed_compose_is_a_failed_command(self):
        self.env['FAKE_DOCKER_FAIL']='1'
        self.assertEqual(self.run_launcher('up').returncode,17)
    def test_deploy_requires_immutable_image(self):
        self.env['FOLIOLET_IMAGE']='ghcr.io/example/foliolet:latest'
        self.assertNotEqual(self.run_launcher('deploy').returncode,0)

if __name__=='__main__':unittest.main(verbosity=2)
