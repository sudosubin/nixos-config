#!/usr/bin/env python3
"""Actual kernel/output pilot tests, ONLY within an owned private verify fence."""
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import spot_validation as validation
import spot_shadow as p


class ShadowLinuxTests(unittest.TestCase):
    def setUp(self):
        budget = validation.current()
        self.assertTrue(budget and budget['purpose'] in {'verify', 'canary-verify'})
        self.assertEqual(os.geteuid(), 0)
        self.temp = tempfile.TemporaryDirectory(prefix='spot-shadow-owned-')
        self.root = Path(self.temp.name); self.root.chmod(0o700)
        self.store = p.Store(self.root)
        self.binding = {'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                        'instance': 'i-00000000000000000'}
        self.store.initialize(self.binding)

    def tearDown(self): self.temp.cleanup()

    def test_real_user_drop_stdout_stderr_and_no_delivery_claim(self):
        body = ('import os,json;from pathlib import Path;'
                'print(json.dumps(dict(uid=os.getuid(),groups=os.getgroups(),'
                'nnp="NoNewPrivs:\\t1" in Path("/proc/self/status").read_text(),'
                'stdin=os.readlink("/proc/self/fd/0"),aws_keys=[k for k in os.environ if k.startswith("AWS_")])));'
                'os.write(2,b"synthetic stderr\\n")')
        result = p.run(self.store, self.binding, [sys.executable, '-B', '-I', '-c', body])
        self.assertEqual(result['exit_status'], 0)
        job = self.store.job(result['job'])
        value = json.loads((job/'stdout').read_text())
        self.assertEqual(value['uid'], 1001); self.assertEqual(value['groups'], [])
        self.assertTrue(value['nnp']); self.assertEqual(value['stdin'], '/dev/null')
        self.assertEqual(value['aws_keys'], [])
        self.assertEqual((job/'stderr').read_text(), 'synthetic stderr\n')
        self.assertEqual(result['output_delivery'], 'unverified')
        self.assertEqual(result['output_spool']['stdout'], p.spool_hash(job/'stdout'))
        self.assertFalse(self.store.status()['all_work_idle'])

    def test_real_double_fork_setsid_is_waited_and_output_kept(self):
        body = ('import os,time\npid=os.fork()\nif pid==0:\n os.setsid();pid=os.fork()\n'
                ' if pid==0:\n  time.sleep(.5);os.write(1,b"detached fixture finished\\n")\n'
                ' os._exit(0)\nos._exit(0)')
        started = time.monotonic()
        result = p.run(self.store, self.binding, [sys.executable, '-B', '-I', '-c', body])
        self.assertGreaterEqual(time.monotonic()-started, .45)
        self.assertEqual((self.store.job(result['job'])/'stdout').read_text(), 'detached fixture finished\n')
        self.assertTrue(self.store.status()['jobs'][0]['always_blocks_termination'])

    def test_real_non_SIGCHLD_clone_is_waited(self):
        original = p.work.subprocess.Popen
        def clone(argv, **kwargs):
            child = original(argv, **kwargs)
            number = {'aarch64': 220, 'x86_64': 56}.get(os.uname().machine)
            if number is None: raise RuntimeError('unknown actual clone ABI, no skipped proof')
            libc = ctypes.CDLL(None, use_errno=True)
            pid = libc.syscall(number, 0, 0, 0, 0, 0)
            if pid < 0: raise OSError(ctypes.get_errno(), 'owned fixture clone failed')
            if pid == 0:
                os.execv(sys.executable, [sys.executable, '-B', '-I', '-c',
                         'import time,os;time.sleep(.5);os.write(1,b"clone fixture finished\\n")'])
            return child
        started = time.monotonic()
        with patch.object(p.work.subprocess, 'Popen', side_effect=clone):
            result = p.run(self.store, self.binding, [sys.executable, '-B', '-I', '-c', 'pass'])
        self.assertGreaterEqual(time.monotonic()-started, .45)
        self.assertIn('clone fixture finished', (self.store.job(result['job'])/'stdout').read_text())
        self.assertEqual(result['output_delivery'], 'unverified')

    def test_real_missing_payload_keeps_local_output_and_unknown(self):
        result = p.run(self.store, self.binding, ['/does-not-exist/owned-synthetic-fixture'])
        self.assertNotEqual(result['exit_status'], 0)
        self.assertTrue(self.store.status()['jobs'][0]['always_blocks_termination'])
        self.assertTrue((self.store.job(result['job'])/'stderr').stat().st_size)

    def test_real_lost_spawn_receipt_never_retires_or_replays(self):
        owned = {}
        def uncertain(argv, **kwargs):
            pid = os.fork()
            if pid == 0:
                os.setsid(); os.execv(argv[0], argv)
            owned['pid'] = pid
            raise OSError('owned fixture lost receipt AFTER native fork')
        with patch.object(p.work.subprocess, 'Popen', side_effect=uncertain):
            with self.assertRaises(OSError):
                p.run(self.store, self.binding, [sys.executable, '-B', '-I', '-c',
                      'import time,os;time.sleep(.3);os.write(1,b"late synthetic output\\n")'])
        waited, status = os.waitpid(owned['pid'], 0x40000000)
        self.assertEqual(waited, owned['pid']); self.assertEqual(status, 0)
        jobs = self.store.status()['jobs']; self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['state'], 'lease_before_possible_spawn')
        self.assertEqual((self.store.job(jobs[0]['id'])/'stdout').read_text(), 'late synthetic output\n')
        self.assertTrue(jobs[0]['always_blocks_termination'])

    def test_real_owned_wrapper_crash_does_not_stop_child_or_clear_record(self):
        p.work.subreaper()
        payload = ('import os,time;print(os.getpid(),flush=True);time.sleep(.5);'
                   'os.write(1,b"child survived owned wrapper crash\\n")')
        helper = ('import sys,json;sys.path.insert(0,'+repr(str(Path(p.__file__).parent))+');'
                  'import spot_shadow as p;'
                  'p.run(p.Store('+repr(str(self.root))+'),'+repr(self.binding)+','
                  +repr([sys.executable,'-B','-I','-c',payload])+')')
        with subprocess.Popen([sys.executable,'-B','-I','-c',helper], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True) as wrapper:
            deadline = time.monotonic()+5; paths=[]; first=''
            while time.monotonic()<deadline:
                paths = list((self.root/'jobs').iterdir())
                if paths and (paths[0]/'stdout').exists(): first=(paths[0]/'stdout').read_text()
                if first: break
                time.sleep(.005)
            self.assertTrue(first, 'owned fixture did not start')
            payload_pid = int(first.splitlines()[0]); wrapper.kill()
            out, err = wrapper.communicate(timeout=5)
            self.assertEqual(wrapper.returncode, -9, err)
            waited, status = os.waitpid(payload_pid, 0x40000000)
            self.assertEqual(waited, payload_pid); self.assertEqual(status, 0)
        record = p.Store(self.root).status()['jobs'][0]
        self.assertEqual(record['state'], 'lease_before_possible_spawn')
        self.assertIn('child survived owned wrapper crash', (paths[0]/'stdout').read_text())
        self.assertTrue(record['always_blocks_termination'])

    def test_low_reserve_rejects_before_lease_or_spawn(self):
        class Low: f_bavail = 1; f_frsize = 4096
        with patch.object(p.os, 'statvfs', return_value=Low()), patch.object(p.work, 'run_job') as job:
            with self.assertRaises(RuntimeError): p.run(self.store, self.binding, [sys.executable, '-c', 'pass'])
            job.assert_not_called()
        self.assertEqual(self.store.status()['jobs'], [])


if __name__ == '__main__': unittest.main()
