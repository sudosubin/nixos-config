#!/usr/bin/env python3
"""Private synthetic native-fixture helper: replacement output console, not ACK.

Called only after the existing native verifier's owned controller/actor exited.
No provider RPC/input, takeover, original record modification or global signals.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import sys
import time
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).parent))
import spot_shadow_review as r


def exercise(store,folder,evidence,cli=None):
    budget=r.validation.current()
    r.shadow.require(budget and budget['purpose'] in {'verify','canary-verify'},'private owned native review fixture required')
    evidence=Path(evidence);evidence.mkdir(mode=0o700)
    selected=r.selected(store,folder);target=store.job(selected['session']);parent_before=(target/'record.json').read_bytes()
    old={path.name for path in (store.root/'jobs').iterdir()};actors=[];consoles={};active=[]
    invocation=([str(cli)] if cli else [sys.executable,'-B','-I',str(Path(r.__file__)),
        '--expected-version',r.version(Path(r.__file__).parent),'--store',str(store.root)])
    def spawn(label,prepare=False):
        master,slave=pty.openpty()
        command=[*invocation,'--tui-session',str(folder),'review','--from-start']
        if prepare:command.append('--prepare-new-review')
        gate='import os,sys,fcntl,termios;fcntl.ioctl(0,termios.TIOCSCTTY,0);os.execv(sys.argv[1],sys.argv[1:])'
        child=subprocess.Popen([sys.executable,'-B','-I','-c',gate,*command],stdin=slave,stdout=slave,stderr=slave,start_new_session=True)
        os.close(slave);active.append((child,master));value={'child':child,'master':master,'start':r.work.process_start(child.pid),'label':label,'console':bytearray()};actors.append(value);return value
    def read(value):
        while select.select([value['master']],[],[],0)[0]:
            try:data=os.read(value['master'],65536)
            except OSError:break
            if not data:break
            value['console'].extend(data)
            r.shadow.require(len(value['console'])<2*1024**2,'synthetic review console bound exceeded')
        return bytes(value['console'])
    def wait(value,predicate,label,alive=True):
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            read(value)
            if predicate():return
            if alive:r.shadow.require(value['child'].poll() is None,'owned review exited before '+label)
            time.sleep(.02)
        raise RuntimeError('review fixture condition missing: '+label)
    def lease(value):
        for path in (store.root/'jobs').iterdir():
            if path.name in old:continue
            try:row=r.shadow.read(path/'record.json')
            except FileNotFoundError:continue  # never an approval; wait for this exact PID receipt
            if row.get('kind')=='shadow_output_review' and row['pid']==value['child'].pid and row['pid_start']==value['start']:return row
        return {}
    def owned_fd(value):
        def check():
            pid=value['child'].pid
            r.shadow.require(r.work.process_start(pid)==value['start'] and r.work.process_uid(pid)==0
                and Path('/proc/'+str(pid)+'/cgroup').read_text().strip()=='0::'+budget['cgroup']
                and os.readlink('/proc/'+str(pid)+'/ns/pid')==os.readlink('/proc/self/ns/pid') and os.getpgid(pid)==pid,
                'review signal target not exact newly owned fixture')
        check();fd=os.pidfd_open(value['child'].pid,0)
        try:check()
        except BaseException:os.close(fd);raise
        return fd
    try:
        first=spawn('first-review',True)
        wait(first,lambda:b'END REVIEW PAGE 1;' in read(first) and lease(first).get('rendered_pages')==1,'actual replacement console page')
        first_lease=lease(first);before_conflict={path.name for path in (store.root/'jobs').iterdir()};conflict=spawn('conflicting-review')
        wait(conflict,lambda:conflict['child'].poll() is not None,'kernel conflict refused',alive=False)
        r.shadow.require(conflict['child'].returncode==75 and b'REVIEW CONFLICT:' in read(conflict)
                         and b'REVIEW PAGE ' not in read(conflict) and not lease(conflict)
                         and before_conflict=={path.name for path in (store.root/'jobs').iterdir()},
                         'concurrent review was not refused before page/lease')
        fd=owned_fd(first)
        try:
            signal.pidfd_send_signal(fd,signal.SIGKILL,None,0)
            wait(first,lambda:bool(select.select([fd],[],[],0)[0]),'owned viewer pidfd exit',alive=False)
        finally:os.close(fd)
        first['child'].wait(timeout=5)
        r.shadow.require((target/'record.json').read_bytes()==parent_before,'review crash changed original keeper record')
        replacement=spawn('explicit-output-rereview')
        page=1
        wait(replacement,lambda:b'END REVIEW PAGE 1;' in read(replacement) and lease(replacement).get('rendered_pages')==1,'fresh explicit output review')
        while page<128:
            os.write(replacement['master'],b'n')  # once per positively observed page, not uncertain key replay
            wait(replacement,lambda:b'REVIEW WAITING:' in read(replacement) or
                ('END REVIEW PAGE '+str(page+1)+';').encode() in read(replacement) and lease(replacement).get('rendered_pages')==page+1,
                'next observed page or pending tail')
            if b'REVIEW WAITING:' in read(replacement):break
            page+=1
        else:raise RuntimeError('review fixture page bound exceeded')
        output=read(replacement)
        r.shadow.require(b'ENTRY_FIRST_MOCK_OUTPUT' in output and b'MUST_NOT_REPLAY_MODEL' not in output,
                         'replacement console did not recover actual late fixture output')
        os.write(replacement['master'],b'q');wait(replacement,lambda:replacement['child'].poll() is not None,'explicit non-ACK close',alive=False)
        r.shadow.require(replacement['child'].returncode==0,'read-only console did not close naturally')
        final=lease(replacement);r.shadow.require(final['state']=='review_closed_output_pending' and final['consumer_delivery']=='unverified'
            and final['id']!=first_lease['id'] and (target/'record.json').read_bytes()==parent_before,
            'view close retired, replayed or modified original work')
        proof={'fixture_only':True,'actual_replacement_console_recovered_late_output':True,
            'conflicting_viewer_refused_before_lease_or_page':True,'owned_first_viewer_pidfd_crash_observed':True,
            'explicit_new_output_review_after_exact_viewer_exit':True,'first_review':first_lease['id'],
            'replacement_review':final['id'],'rendered_pages':page,'original_record_sha256':hashlib.sha256(parent_before).hexdigest(),
            'no_provider_connection_input_or_execution':True,'q_is_NOT_delivery_ACK':True,
            'trusted_consumer_delivery_verified':False,'keeper_crash_takeover_verified':False,'goal_complete':False}
        r.shadow.publish(evidence/'proof.json',proof,new=True)
        return proof
    finally:
        for value in actors:
            child=value['child']
            if child.poll() is None:
                # Only this newly created read-only synthetic viewer; never backend/user work.
                try:
                    fd=owned_fd(value)
                    try:signal.pidfd_send_signal(fd,signal.SIGTERM,None,0)
                    finally:os.close(fd)
                except (FileNotFoundError,ProcessLookupError):pass
                child.wait(timeout=5)
            read(value);(evidence/(value['label']+'-full-pty.bin')).write_bytes(value['console']);os.close(value['master'])
        snapshot={'fixture_only':True,'records':{}}
        for path in (store.root/'jobs').iterdir():
            if path.name in old:continue
            data=(path/'record.json').read_bytes();snapshot['records']['jobs/'+path.name+'/record.json']={'bytes':len(data),
                'sha256':hashlib.sha256(data).hexdigest(),'body_base64':base64.b64encode(data).decode()}
        for path in (target/'output-review').rglob('*'):
            if not path.is_file() or path.name=='lock':continue
            data=path.read_bytes();snapshot['records']['output-review/'+str(path.relative_to(target/'output-review'))]={'bytes':len(data),
                'sha256':hashlib.sha256(data).hexdigest(),'body_base64':base64.b64encode(data).decode()}
        r.shadow.publish(evidence/'complete-owned-fixture-snapshot.json',snapshot,new=True)
