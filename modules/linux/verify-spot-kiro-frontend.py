#!/usr/bin/env python3
"""Real pinned native/TUI + local-queue custody, with mock model and empty HOME.

Root Linux/private PID1+mount+network, NoNewPrivileges, tools/hooks/MCP absent.
Never use host user state or the production admission registry. No real provider
completion, whole-worker verification, production rollout or reboot is claimed.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pty
import pwd
import re
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest

spec=importlib.util.spec_from_file_location('native_fixture',Path(__file__).with_name('verify-spot-kiro-native.py'))
n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
OPTIONS=None


class FrontendNativeTests(unittest.TestCase):
    setUp=n.NativeKiroTests.setUp
    cleanup=n.NativeKiroTests.cleanup
    demote=n.NativeKiroTests.demote
    records=n.NativeKiroTests.all_records
    await_condition=n.NativeKiroTests.await_condition

    def fronts(self):return [x for x in self.records() if x.get('kind')=='kiro_frontend']
    def acps(self):return [x for x in self.records() if x.get('kind')=='acp']
    def acp_idle(self):
        rows=self.acps()
        return len(rows)==1 and rows[0]['initialized'] and rows[0]['healthy'] and rows[0]['active_requests']==0

    def gui(self,queue=False):
        self.mock.write_text(json.dumps([['MODEL_FREE_FRONT_FIRST'],['MODEL_FREE_FRONT_SECOND']]))
        env={**self.env}
        command=[OPTIONS.launcher,'--agent','spot-canary']
        if queue:
            entry=self.base/'queue-entry.mjs';source=Path(OPTIONS.entry).read_text()
            marker='await import(pathToFileURL(tui).href);';self.assertEqual(source.count(marker),1)
            # A real vendor UI setting, changed ONLY in this isolated fixture.
            # No mock client, GET_STORE/test IPC, authentication bypass or gate
            # override. Keyboard input still travels through real vendor code.
            setting="const modeTimer=setInterval(()=>{const h=globalThis[Symbol.for('nixos.spot.kiro.frontend.v1')];if(h?.store){h.store.getState().setActiveInterruptMode('queue');clearInterval(modeTimer);}},5);modeTimer.unref();\n"
            entry.write_text(source.replace(marker,setting+marker));entry.chmod(0o644)
            env.update(PATH=str(n.PUBLIC)+':'+env['PATH'],KIRO_TEST_TUI_JS_PATH=str(entry))
            command=[OPTIONS.fronttool,'launch','--',OPTIONS.frontend,'chat','--tui','--agent-engine','v2','--agent','spot-canary']
        master,slave=pty.openpty();self.masters.append(master)
        fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,120,0,0))
        try:child=subprocess.Popen(command,stdin=slave,stdout=slave,stderr=slave,env=env,cwd=self.home,preexec_fn=self.demote(slave))
        finally:os.close(slave)
        self.children.append(child);self.console=bytearray()
        def read():
            while select.select([master],[],[],0)[0]:
                try:data=os.read(master,65536)
                except OSError:break
                if not data:break
                self.console.extend(data)
                if b'\x1b[6n' in data:os.write(master,b'\x1b[1;1R')
            self.assertLess(len(self.console),2*1024*1024)
            self.last_console=re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',b'',bytes(self.console))
            return self.last_console
        self.read_console=read
        return child,master

    def ready(self,child):
        self.read_console();self.assertIsNone(child.poll(),'isolated native UI exited before readiness')
        rows=self.fronts()
        return self.acp_idle() and len(rows)==1 and rows[0]['healthy'] and rows[0]['initialized'] and rows[0].get('epoch') is None

    def pause_backend(self):
        row=self.acps()[0];pid=row['backend_pid']
        self.assertEqual(n.work.process_start(pid),row['backend_start'])
        self.assertEqual(n.work.process_uid(pid),1001)
        self.paused=(pid,row['backend_start']);os.kill(pid,signal.SIGSTOP)
        return pid

    def resume_backend(self,pid):
        os.kill(pid,signal.SIGCONT);self.paused=None

    def test_actual_local_queue_is_leased_before_second_backend_request_and_survives_refused_seal(self):
        child,master=self.gui(queue=True);self.await_condition(lambda:self.ready(child))
        backend=self.pause_backend()
        try:
            os.write(master,b'First private model-free fixture.\r')
            self.await_condition(lambda:(self.read_console() is not None and self.acps()[0]['active_requests']==1))
            os.write(master,b'Second private locally queued fixture.\r')
            self.await_condition(lambda:(self.read_console() is not None and self.fronts()[0].get('counters',{}).get('queued')==1))
            front=self.fronts()[0];epoch=json.loads((self.protocol.leases/front['epoch']).read_text())
            self.assertEqual(epoch['pid'],front['pid']);self.assertEqual(epoch['pid_start'],front['pid_start'])
            self.assertEqual(self.acps()[0]['active_requests'],1,'local queue must not already be a backend request')
            with self.assertRaises(n.work.SealBlocked):self.protocol.seal()
            self.assertEqual(self.protocol.state(),'open')
        finally:self.resume_backend(backend)
        self.await_condition(lambda:(b'MODEL_FREE_FRONT_FIRST' in self.read_console() and b'MODEL_FREE_FRONT_SECOND' in self.read_console() and self.ready(child)))
        self.assertEqual(self.fronts()[0]['admission_rejections'],0)
        self.assertTrue(all(x['reason']=='participant_unverified' for x in self.protocol.blockers()))
        with self.assertRaises(n.work.SealBlocked):self.protocol.seal()

    def test_actual_closed_fault_fence_rejects_before_store_queue_without_killing_admitted_turn(self):
        child,master=self.gui();self.await_condition(lambda:self.ready(child));backend=self.pause_backend()
        try:
            os.write(master,b'Admitted private model-free fixture.\r')
            self.await_condition(lambda:(self.read_console() is not None and self.acps()[0]['active_requests']==1))
            with self.protocol.locked():self.protocol.write_state('draining')  # private fault only
            os.write(master,b'Must not become accepted queued work.\r')
            self.await_condition(lambda:(self.read_console() is not None and self.fronts()[0]['admission_rejections']>=1))
            self.await_condition(lambda:b'input not accepted' in self.read_console())
            self.assertEqual(self.fronts()[0]['counters']['queued'],0)
            self.assertEqual(self.acps()[0]['active_requests'],1)
            self.assertEqual(self.acps()[0]['admission_rejections'],0,'rejection must precede ACP forwarding')
        finally:self.resume_backend(backend)
        self.await_condition(lambda:b'MODEL_FREE_FRONT_FIRST' in self.read_console() and self.acp_idle())
        self.assertNotIn(b'MODEL_FREE_FRONT_SECOND',self.read_console())
        self.assertTrue(self.protocol.blockers())  # preserved draft/participant is NOT idle authority

    def test_actual_changed_vendor_bundle_refuses_uninstrumented_fallback(self):
        tui=self.home/'.local/share/kiro-cli/tui.js';tui.unlink();tui.write_text('// changed vendor fixture\n');tui.chmod(0o644)
        child,master=self.gui()
        self.await_condition(lambda:(self.read_console() is not None and child.poll() is not None))
        self.assertNotEqual(child.returncode,0)
        self.assertEqual(self.acps(),[])
        self.assertTrue(self.protocol.blockers())
        self.assertTrue(self.fronts() and self.fronts()[0]['healthy'] is False)


def main():
    global OPTIONS
    p=argparse.ArgumentParser(description=__doc__)
    names=['frontend','backend','bun','tui','proxy','launcher','entry','fronttool']
    for name in names:p.add_argument('--'+name,required=True)
    p.add_argument('--inside-private-namespaces',action='store_true',help=argparse.SUPPRESS)
    OPTIONS=p.parse_args()
    if sys.platform!='linux' or os.geteuid()!=0:p.error('requires explicit root Linux; skipping is not proof')
    for name in names:setattr(OPTIONS,name,str(Path(getattr(OPTIONS,name)).resolve(strict=True)))
    n.OPTIONS=OPTIONS
    if not OPTIONS.inside_private_namespaces:
        return subprocess.call(['unshare','--mount','--net','--pid','--fork','--mount-proc','--kill-child',sys.executable,str(Path(__file__).resolve()),*sys.argv[1:],'--inside-private-namespaces'])
    if os.getpid()!=1:p.error('requires fresh private PID namespace')
    subprocess.run(['mount','--make-rprivate','/'],check=True);n.USER=pwd.getpwuid(1001)
    with tempfile.TemporaryDirectory(prefix='spot-frontend-public-',dir='/run') as directory:
        n.PUBLIC=Path(directory);n.PUBLIC.chmod(0o755);hashes={}
        for name,source in [('bun',OPTIONS.bun),('tui.js',OPTIONS.tui)]:
            target=n.PUBLIC/name;shutil.copyfile(source,target);target.chmod(0o555 if name=='bun' else 0o444)
            hashes[name]=hashlib.sha256(target.read_bytes()).hexdigest()
        for index,target in enumerate(['/home','/root','/tmp','/run/user']):
            empty=n.PUBLIC/('empty-'+str(index));empty.mkdir();empty.chmod(0o1777 if target=='/tmp' else 0o755)
            subprocess.run(['mount','--bind',str(empty),target],check=True)
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FrontendNativeTests))
        print(json.dumps({'frontend_native_cases':result.testsRun,'skipped':len(result.skipped),'failures':len(result.failures),'errors':len(result.errors),'vendor_sha256':hashes,'real_models_credentials_channels':False,'private_PID1_mount_network':True,'whole_tracking_verified':False,'production_rollout':False}),flush=True)
        return 0 if result.wasSuccessful() and result.testsRun==3 and not result.skipped else 1


if __name__=='__main__':sys.exit(main())
