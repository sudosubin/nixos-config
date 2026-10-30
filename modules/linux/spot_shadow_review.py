#!/usr/bin/env python3
"""Explicit replacement OUTPUT console; no backend connection/input/takeover.

Every view is newly leased. Deliberate --from-start reviews OUTPUT, never work.
Terminal write return, cursor, q and EOF are NOT recipient delivery/idle authority.
Original TUI/controller must have conclusively exited in the exact same epoch.
"""
import argparse
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import termios
import time
import tty
import uuid
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).parent))
import spot_shadow as shadow
import spot_shadow_acp as acp
import spot_validation as validation
import spot_work as work

SOURCES=['spot_work.py','spot_shadow.py','spot_acp.py','spot_shadow_acp.py','spot_validation.py','spot_shadow_review.py']
PAGE=2048


def version(folder):
    return hashlib.sha256(''.join(hashlib.sha256((Path(folder)/name).read_bytes()).hexdigest() for name in SOURCES).encode()).hexdigest()[:12]


def boot():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()

def namespace():return os.readlink('/proc/self/ns/pid')


def exited(owner):
    """Exact old process only, NEVER whole-server idle or backend ownership."""
    epoch=boot();ns=namespace()
    shadow.require(owner['boot_id']==epoch and owner['pid_namespace']==ns
        and type(owner['pid']) is int and owner['pid']>1 and type(owner['pid_start']) is int,
        'old consumer epoch/namespace unknown; no replacement')
    try:gone=work.process_start(owner['pid'])!=owner['pid_start']
    except (FileNotFoundError,ProcessLookupError):gone=True
    shadow.require(boot()==epoch and namespace()==ns,'process epoch changed during observation')
    return gone


def selected(store,folder):
    store.check();folder=Path(folder);st=folder.lstat()
    shadow.require(stat.S_ISDIR(st.st_mode) and st.st_uid==store.owner and not st.st_mode&0o022
        and re.fullmatch('[0-9a-f]{32}',folder.name),'untrusted TUI session')
    session=shadow.read(folder/'session.json',store.owner);front=shadow.read(folder/'frontend.json',store.owner)
    intent=shadow.read(folder/'keeper-start-intent.json',store.owner);d=shadow.read(folder/'keeper.json',store.owner)
    shadow.require(session['id']==folder.name and front['keeper']==d and intent['startup']==front['startup']
        and intent['boot_id']==session['binding']['boot_id']==d['boot_id']==boot(),
        'session/keeper/startup binding changed; no recovery')
    startup=shadow.read(store.job(front['startup'])/'record.json',store.owner)
    parent=shadow.read(store.job(d['session'])/'record.json',store.owner)
    shadow.require(startup.get('kind')=='shadow_tui_startup' and parent.get('kind')=='acp_keeper'
        and startup['instance']==parent['instance']==session['binding']['instance']
        and startup['boot_id']==parent['boot_id']==d['boot_id'] and parent['pid']==d['pid']
        and parent['pid_start']==d['pid_start'],'unknown output lineage')
    shadow.require(exited(startup),'original controller still alive; no replacement')
    actors=[]
    for path in (store.root/'jobs').iterdir():
        # A partial/malformed record is unknown, NOT an empty roster.
        row=shadow.read(path/'record.json',store.owner)
        if row.get('parent_startup')==startup['id'] and row.get('kind')=='shadow_kiro_frontend':actors.append(row)
    shadow.require(len(actors)==1,'original actor binding missing/conflicting')
    actor=actors[0]['actor']
    shadow.require(actor.get('uid')==1001 and actor.get('pid_namespace')==startup['pid_namespace'],
                   'original actor identity incomplete')
    shadow.require(exited(dict(actor,boot_id=actors[0]['boot_id'])),'original TUI actor still alive; no replacement')
    spool=store.job(d['session'])/'output';shadow.directory(spool,store.owner);st=spool.stat()
    return {'schema':1,'session':d['session'],'startup':startup['id'],'boot_id':boot(),
        'instance':parent['instance'],'spool_device':st.st_dev,'spool_inode':st.st_ino,
        'mode':'readonly_output_review_NOT_input_or_delivery','termination_capable':False}


def provision(store,selection):
    """Explicit one-time review namespace, not a canonical work initialization."""
    root=store.job(selection['session'])/'output-review'
    shadow.require(not os.path.lexists(root),'review namespace exists/partial; never seed/reset over it')
    root.mkdir(mode=0o700);shadow.sync_directory(root.parent)
    fd=os.open(root/'lock',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);os.close(fd)
    (root/'views').mkdir(mode=0o700)
    shadow.publish(root/'seed.json',selection,new=True)


class ReviewConflict(RuntimeError):pass


class Review:
    def __init__(self,store,folder):
        self.store,self.folder=store,Path(folder);self.selection=selected(store,folder)
        self.target=store.job(self.selection['session']);self.root=self.target/'output-review'
        shadow.directory(self.root,store.owner);shadow.directory(self.root/'views',store.owner)
        shadow.require(shadow.read(self.root/'seed.json',store.owner)==self.selection,'review seed/spool changed; no reset')
        self.fd=os.open(self.root/'lock',os.O_WRONLY|os.O_NOFOLLOW);self.lease=None
        try:
            st=os.fstat(self.fd)
            shadow.require(stat.S_ISREG(st.st_mode) and st.st_uid==store.owner and stat.S_IMODE(st.st_mode)==0o600,
                           'review lock ownership unknown')
            try:fcntl.flock(self.fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise ReviewConflict('authenticated output view active') from None
            # Recheck original identities and spool after acquiring the lock.
            shadow.require(selected(store,folder)==self.selection,'review selection changed')
            self.lease=store.create({'instance':self.selection['instance'],'boot_id':self.selection['boot_id']},
                                   ['explicit output review; no provider input or content in metadata'])
            store.update(self.lease,kind='shadow_output_review',related_session=self.selection['session'],
                state='review_leased_before_terminal_effect',consumer_delivery='unverified',
                rendered_pages=0,output_reexecution=False,provider_input_replayed=False)
            shadow.publish(self.root/'views'/self.lease['id'],{'review':self.lease['id'],
                'pid':os.getpid(),'pid_start':self.lease['pid_start'],'consumer_delivery':'unverified'},new=True)
        except BaseException:os.close(self.fd);self.fd=None;raise

    def state(self,**changes):self.store.update(self.lease,**changes)

    def read(self,sequence):
        shadow.require(self.selection==shadow.read(self.root/'seed.json',self.store.owner),'review seed changed')
        st=(self.target/'output').stat()
        shadow.require((st.st_dev,st.st_ino)==(self.selection['spool_device'],self.selection['spool_inode']),
                       'output spool replaced; no recovery read')
        row=shadow.read(self.target/'record.json',self.store.owner);count=row.get('output_segments')
        shadow.require(type(count) is int and 0<=count<=65536 and type(sequence) is int and 0<=sequence<=count,
                       'output inventory unknown; never skip missing frames')
        if sequence==count or not (self.target/'output'/(str(sequence).zfill(12)+'.exposed')).exists():
            # Even a locally terminal tail is NOT delivered/empty/retirable.
            return None
        return acp.Segments.read(self.target/'output',sequence,self.store.owner)

    def close(self):
        if self.fd is not None:os.close(self.fd);self.fd=None


def safe_text(data):
    # Literal human-readable Unicode; escape controls, bidi/format characters,
    # invalid UTF-8 and backslashes. Output can never inject OSC/CSI/terminal RPC.
    result=[]
    for char in data.decode('utf-8','surrogateescape'):
        n=ord(char)
        if char=='\\':result.append('\\\\')
        elif char=='\n' or char.isprintable():result.append(char)
        elif 0xdc80<=n<=0xdcff:result.append('\\x'+format(n-0xdc00,'02x'))
        elif n<=255:result.append('\\x'+format(n,'02x'))
        else:result.append('\\u'+format(n,'04x'))
    return ''.join(result)


def terminal(review,write,key):
    sequence=0;offset=0;page=0;row=None;text=None
    try:
        while True:
            if row is None:
                row=review.read(sequence)
                if row is None:
                    review.state(state='review_waiting_output_exposure_NOT_complete',next_sequence=sequence)
                    write('REVIEW WAITING: output exposure pending/unknown; r=inspect again, q=leave. NOT delivered.\n')
                    action=key()
                    if action=='r':continue
                    if action=='q' or not action:break
                    continue
                body=base64.b64decode(row['data_base64'],validate=True)
                text=safe_text(body);offset=0
            chunk=text[offset:offset+PAGE];page+=1
            review.state(state='review_terminal_write_attempted_unknown',presentation={'sequence':sequence,
                'channel':row['channel'],'sha256':row['sha256'],'display_offset':offset,'page':page})
            # Exactly one bounded page effect. Lost/partial write: never retry,
            # advance cursor, consume another frame, or call this delivery.
            write('REVIEW PAGE '+str(page)+' segment='+str(sequence)+' channel='+row['channel']+'\n'+chunk+
                  '\nEND REVIEW PAGE '+str(page)+'; n=next, q=leave; NOT delivery acknowledgement.\n')
            review.state(state='review_terminal_write_returned_NOT_delivery',rendered_pages=page)
            action=key()
            if action=='q' or not action:break
            while action!='n':
                action=key()
                if action=='q' or not action:break
            if action!='n':break
            offset+=len(chunk)
            if offset>=len(text):sequence+=1;row=None;text=None
        review.state(state='review_closed_output_pending',consumer_delivery='unverified')
        return 0
    except BaseException:
        try:review.state(state='review_presentation_or_custody_uncertain_no_retry',consumer_delivery='unverified')
        except (OSError,ValueError,RuntimeError):pass
        raise


def resource_gate():
    budget=validation.current()
    if budget is not None:
        shadow.require(budget['purpose'] in {'verify','canary-verify'},'review cannot borrow build authority')
        return budget
    shadow.collector_gate()  # bounded private 256MiB/CPU25 metadata/data reader only
    group=Path('/proc/self/cgroup').read_text().strip().split('::')[-1]
    shadow.require(re.fullmatch('/system.slice/spot-shadow-output-review-[0-9a-f]{32}.service',group),
                   'unowned review reader cage')
    return {'readonly_output_reader':True,'memory_max':256*1024**2,'build_or_verification_authority':False}


def launch(args):
    shadow.require(os.geteuid()==0 and os.isatty(0) and os.isatty(1),'root interactive cloud TTY required')
    shadow.require(validation.current() is None,'no nested application budget; fixtures use review within their exact budget')
    shadow.require(validation.available_memory(Path('/proc/meminfo').read_text())>=2*1024**3,
                   'insufficient memory reserve for bounded output reader')
    name='spot-shadow-output-review-'+uuid.uuid4().hex
    command=['systemd-run','--pty','--wait','--collect','--unit='+name,'-p','Type=exec',
        '-p','MemoryMax=256M','-p','MemorySwapMax=0','-p','CPUQuota=25%','-p','OOMPolicy=kill',
        '-p','OOMScoreAdjust=1000','-p','Nice=19','-p','NoNewPrivileges=yes','-p','PrivateNetwork=yes',
        '-p','ProtectControlGroups=yes',sys.executable,'-B','-I',str(Path(__file__)),
        '--expected-version',args.expected_version,'--store',str(args.store),'--tui-session',str(args.tui_session),
        'review','--from-start']
    if args.prepare_new_review:command.append('--prepare-new-review')
    # No provider/native process, runtime deadline, stop/restart or global reload.
    return subprocess.call(command)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--expected-version',required=True)
    parser.add_argument('--store',type=Path,required=True);parser.add_argument('--tui-session',type=Path,required=True)
    parser.add_argument('action',choices=['launch','review']);parser.add_argument('--from-start',action='store_true')
    parser.add_argument('--prepare-new-review',action='store_true');args=parser.parse_args()
    shadow.require(os.geteuid()==0 and args.expected_version==version(Path(__file__).parent),'root/pinned review source required')
    shadow.require(args.from_start,'explicit --from-start OUTPUT review required; never resume/replay input')
    if args.action=='launch':return launch(args)
    resource_gate();shadow.require(os.isatty(0) and os.isatty(1) and os.ttyname(0)==os.ttyname(1),
                                  'review requires same interactive recipient TTY, never a pipe/file ACK')
    store=shadow.Store(args.store)
    if args.prepare_new_review:provision(store,selected(store,args.tui_session))
    review=Review(store,args.tui_session);saved=termios.tcgetattr(0)
    def write(text):
        data=text.encode('utf-8');count=os.write(1,data)
        shadow.require(count==len(data),'terminal write partial/unknown; no retry')
    try:
        tty.setcbreak(0)
        return terminal(review,write,lambda:os.read(0,1).decode('ascii','ignore'))
    finally:termios.tcsetattr(0,termios.TCSANOW,saved);review.close()


if __name__=='__main__':
    try:sys.exit(main())
    except ReviewConflict:
        print('REVIEW CONFLICT: no new lease/page; original view and backend unchanged',file=sys.stderr)
        sys.exit(75)
    except (OSError,ValueError,RuntimeError):
        print('Read-only review unavailable/uncertain; original work/output retained; no replay or delivery approval',file=sys.stderr)
        sys.exit(75)
