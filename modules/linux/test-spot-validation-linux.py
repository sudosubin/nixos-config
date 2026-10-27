#!/usr/bin/env python3
"""Observe real kernel budgets and service inheritance inside the private cage.
No deliberate OOM/global pressure, real provider, production service or AWS IO.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
import spot_validation as validation


def systemctl(*args):
    return subprocess.run(['systemctl',*args],capture_output=True,text=True,timeout=15,check=True).stdout


class ResourceLinuxTests(unittest.TestCase):
    def test_actual_kernel_slice_budget_and_child_oom_preference_are_inherited(self):
        budget=validation.current();self.assertIsNotNone(budget);validation.memory_gate()
        body='import json,os;from pathlib import Path;print(json.dumps({"pid":os.getpid(),"cgroup":Path("/proc/self/cgroup").read_text(),"oom":Path("/proc/self/oom_score_adj").read_text()}))'
        result=subprocess.run([sys.executable,'-I','-c',body],capture_output=True,text=True,check=True,
                              env={'PATH':'/run/current-system/sw/bin','HOME':'/var/empty','AWS_EC2_METADATA_DISABLED':'true'})
        child=json.loads(result.stdout);self.assertEqual(child['oom'].strip(),'1000')
        self.assertEqual(validation.own_group(child['cgroup'])[2],budget['slice_cgroup'])
        self.assertEqual(budget['memory_max'],validation.policy(budget['purpose'])[0]);self.assertEqual(budget['swap_max'],0)

    def test_actual_systemd_fixture_joins_shared_budget_without_restarting_any_production_service(self):
        budget=validation.current();self.assertIsNotNone(budget);validation.memory_gate()
        ident=uuid.uuid4().hex[:12];unit='spot-resource-validation-'+ident+'.service'
        base=Path(tempfile.mkdtemp(prefix='spot-resource-validation-',dir='/run'))
        ready=base/'ready.json';release=base/'release'
        body=('import json,time\nfrom pathlib import Path\n'
              +'p=Path('+repr(str(base))+')\n'
              +'(p/"ready.json").write_text(json.dumps({"cgroup":Path("/proc/self/cgroup").read_text(),"oom":Path("/proc/self/oom_score_adj").read_text()}))\n'
              +'limit=time.monotonic()+15\n'
              +'while not (p/"release").exists():\n if time.monotonic()>limit:raise RuntimeError("private fixture release missing")\n time.sleep(.01)\n')
        script=base/'probe.py';script.write_text(body);script.chmod(0o600)
        unitfile=Path('/run/systemd/system')/unit;self.assertFalse(unitfile.exists())
        props={**validation.fixture_properties(),'Type':'exec','RemainAfterExit':'yes','NoNewPrivileges':'yes',
               'PrivateNetwork':'yes','PrivateTmp':'yes','ProtectHome':'yes','ProtectSystem':'strict',
               'ReadWritePaths':str(base),'StandardOutput':'null','StandardError':'null',
               'ExecStart':sys.executable+' -I '+str(script)}
        unitfile.write_text('[Service]\n'+''.join(k+'='+v+'\n' for k,v in props.items()));unitfile.chmod(0o600)
        try:
            # Fresh UUID files are loaded on StartUnit; never daemon-reload a
            # live slice whose kernel-only OOM-group fence must stay intact.
            systemctl('start',unit)
            limit=time.monotonic()+8
            while not ready.exists():
                self.assertLess(time.monotonic(),limit,'private service never became ready');time.sleep(.02)
            child=json.loads(ready.read_text());self.assertEqual(child['oom'].strip(),'1000')
            ident2,path,leaf,member=validation.own_group(child['cgroup'])
            self.assertEqual(ident2,budget['id']);self.assertEqual(leaf,budget['slice_cgroup']);self.assertEqual(member,unit)
            actual=systemctl('show',unit,'--property=ControlGroup','--value').strip();self.assertEqual(actual,path)
            self.assertEqual(validation.current(),budget)  # child creation must not reset the shared OOM fence
            release.touch()
            while True:
                fields=dict(row.split('=',1) for row in systemctl('show',unit,'-p','SubState','-p','Result','-p','ExecMainCode','-p','ExecMainStatus','-p','MainPID').splitlines())
                if fields.get('SubState')=='exited':break
                self.assertLess(time.monotonic(),limit,'private service did not finish');time.sleep(.02)
            self.assertEqual(fields['Result'],'success');self.assertEqual(fields['ExecMainCode'],'1')
            self.assertEqual(fields['ExecMainStatus'],'0');self.assertEqual(fields['MainPID'],'0')
        finally:
            release.touch()
            # The exact disposable fixture only, never a production unit or a
            # process selected from an untrusted/namespace-local PID number.
            state=systemctl('show',unit,'--property=LoadState','--value').strip()
            if state=='loaded':systemctl('stop',unit)
            elif state!='not-found':raise RuntimeError('private fixture cleanup state unknown')
            unitfile.unlink()
            subprocess.run(['systemctl','reset-failed',unit],capture_output=True,text=True,check=False)
            self.assertEqual(validation.current(),budget)
            shutil.rmtree(base)


def main():
    if sys.platform!='linux' or os.geteuid()!=0:raise RuntimeError('root Linux required; no skip-as-proof')
    if validation.current() is None:raise RuntimeError('run through the canonical bounded validation driver')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ResourceLinuxTests))
    print(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
                      'kernel_budget_and_inheritance_only':True,'deliberate_OOM_tested':False,
                      'production_memory_or_work_idle_verified':False,'production_rollout':False}))
    raise SystemExit(0 if result.wasSuccessful() and not result.skipped and result.testsRun==2 else 1)


if __name__=='__main__':main()
