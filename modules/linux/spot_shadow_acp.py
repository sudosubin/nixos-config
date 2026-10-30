#!/usr/bin/env python3
"""Opt-in root-owned ACP keeper; no canonical ready/idle/arming authority.

Client disconnection never closes backend input or kills work. Requests are
leased before forwarding; admitted IDs are never replayed in this keeper.
Backend output is fsynced in immutable private segments BEFORE it is exposed.
Reading/replaying OUTPUT is not consumer delivery or permission to terminate.
This local spool is not an off-root journal. Existing TUI/Herdr are untouched.
"""
import argparse
import base64
import ctypes
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import socket
import stat
import struct
import subprocess
import sys
import threading
import time
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))
import spot_shadow as shadow
import spot_acp as acp
import spot_work as work

SOURCES = ['spot_work.py', 'spot_shadow.py', 'spot_acp.py', 'spot_shadow_acp.py']
NATIVE_SHA = '1c2a36ec26bae2bdd8d5d7cbb77606f4d072b8bc1a5cfcc6b582ae4a047ce479'
MAX_BYTES = 64 * 1024**2
RESERVE = 2 * 1024**3


def version(folder):
    return hashlib.sha256(''.join(hashlib.sha256((Path(folder)/n).read_bytes()).hexdigest()
                                  for n in SOURCES).encode()).hexdigest()[:12]


def space(path):
    v = os.statvfs(path)
    return v.f_bavail * v.f_frsize


def binary(path):
    h = hashlib.sha256()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        st = os.fstat(stream.fileno())
        shadow.require(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and not st.st_mode & 0o022,
                       'untrusted native backend')
        while data := stream.read(65536): h.update(data)
    return h.hexdigest()


class Segments:
    def __init__(self, directory, owner=0):
        self.directory = Path(directory)
        self.owner = owner
        self.directory.mkdir(mode=0o700)
        shadow.sync_directory(self.directory.parent)
        self.count, self.bytes = 0, 0
        self.lock = threading.RLock()

    def append(self, channel, data):
        shadow.require(channel in {'stdout','stderr'} and isinstance(data, bytes)
                       and 0 < len(data) <= acp.MAX_FRAME+1, 'invalid output segment')
        with self.lock:
            shadow.directory(self.directory, self.owner)
            shadow.require(self.count < 65536 and self.bytes+len(data) <= MAX_BYTES
                           and space(self.directory) >= RESERVE+len(data), 'output_backpressure')
            number = self.count
            path = self.directory/(str(number).zfill(12)+'.bin')
            fd = os.open(path, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd,'wb') as out:
                out.write(data); out.flush(); os.fsync(out.fileno())
            shadow.sync_directory(self.directory)
            row = {'schema':1,'sequence':number,'channel':channel,'bytes':len(data),
                   'sha256':hashlib.sha256(data).hexdigest(),'consumer_delivery':'unverified'}
            shadow.publish(self.directory/(str(number).zfill(12)+'.json'),row,new=True)
            self.count += 1; self.bytes += len(data)
            return row

    @staticmethod
    def read(directory, number, owner=0):
        shadow.require(type(number) is int and 0 <= number < 65536, 'invalid output sequence')
        directory = Path(directory); shadow.directory(directory,owner)
        prefix = str(number).zfill(12)
        row = shadow.read(directory/(prefix+'.json'),owner)
        fd = os.open(directory/(prefix+'.bin'),os.O_RDONLY|os.O_NOFOLLOW)
        with os.fdopen(fd,'rb') as stream:
            st = os.fstat(stream.fileno()); data = stream.read(acp.MAX_FRAME+2)
        shadow.require(stat.S_ISREG(st.st_mode) and st.st_uid==owner and not st.st_mode&0o022
                       and row.get('schema')==1 and row.get('sequence')==number
                       and row.get('channel') in {'stdout','stderr'} and row.get('bytes')==len(data)
                       and len(data)<=acp.MAX_FRAME+1 and row.get('sha256')==hashlib.sha256(data).hexdigest()
                       and row.get('consumer_delivery')=='unverified','output segment uncertain/tampered')
        return dict(row,data_base64=base64.b64encode(data).decode())


class Protocol:
    """Only Tracker's lease API, NOT work.Protocol or startup readiness."""
    def __init__(self, keeper): self.keeper=keeper; self.leases={}

    def create(self, kind):
        k=self.keeper; shadow.require(kind=='job','unsupported shadow custody kind')
        with k.state_lock:
            shadow.require(k.admitting and space(k.store.root)>=RESERVE,
                           'new ACP request not admitted: protection/storage/transport unknown')
            binding=k.protection(); shadow.require(binding==k.binding,'keeper boot/instance changed')
            shadow.require(sum(1 for _ in (k.store.root/'jobs').iterdir())<900,'shadow job capacity reached')
            lease=k.store.create(binding,['ACP request: parameters intentionally omitted'])
            k.store.update(lease,kind='acp_request',parent_session=k.lease['id'],
                           state='request_leased_before_forward',provider_terminal_observed=False)
            self.leases[lease['id']]=lease
            return lease

    def heartbeat(self, lease):
        with self.keeper.state_lock:
            shadow.require(self.leases.get(lease['id']) is lease,'unknown request ownership')
            self.keeper.store.update(lease,heartbeat_at=time.time())

    def terminal(self, lease):
        with self.keeper.state_lock:
            shadow.require(self.leases.get(lease['id']) is lease,'unknown terminal observation')
            self.keeper.store.update(lease,state='provider_terminal_observed_output_pending',
                                     provider_terminal_observed=True)

    def remove(self, *args, **kwargs):
        raise RuntimeError('pipe/spool/read is NOT consumer delivery; shadow custody cannot retire')


class Tracker(acp.Tracker):
    def __init__(self, protocol, publish):
        super().__init__(protocol,publish); self.seen=set()

    def client(self,message,delivered=True):
        with self.lock:
            if isinstance(message,dict) and isinstance(message.get('method'),str) and 'id' in message:
                try: ident=acp.rpc_id(message['id'])
                except ValueError:return super().client(message,delivered)
                if ident in self.seen:
                    return False,acp.error_response(message['id'],-32074,'Previously attempted request; no replay; inspect retained output')
                if message['method'] not in acp.REQUEST_SCOPED|{'session/prompt'} or len(self.seen)>=4096:
                    self.admission_rejections+=1; self.publish(self.state())
                    return False,acp.error_response(message['id'],-32074,'Unsupported ACP route/capacity; request NOT started')
                # Mark BEFORE entering admission/forwarding, including uncertain failures.
                self.seen.add(ident)
            return super().client(message,delivered)

    def backend(self,message,delivered=False):
        with self.lock:
            super().backend(message,delivered=False)
            if isinstance(message,dict) and 'method' not in message:
                try: entry=self.pending.get(acp.rpc_id(message.get('id')))
                except ValueError:entry=None
                if entry and entry['completed']: self.protocol.terminal(entry['lease'])

    def backend_output_delivered(self):
        raise RuntimeError('immutable output retention/read is NOT consumer delivery')


class UncertainChild:
    """Keeper retains pipes and waits its OWN subreaped children, never retries."""
    pid = None
    def poll(self):
        while True:
            try:
                pid, _ = os.waitpid(-1, 0x40000000 | os.WNOHANG)
            except ChildProcessError:
                return 75  # Kernel child-set ended, NOT provider/output completion.
            if pid == 0:
                return None
    def wait(self):
        work.wait_descendants()
        return 75


class Keeper:
    def __init__(self,store,binding,argv,protection):
        self.store,self.binding,self.argv,self.protection=store,binding,argv,protection
        self.state_lock=threading.RLock(); self.input_lock=threading.Lock()
        self.admitting=True; self.finish_requested=False; self.io_uncertain=False
        self.done=threading.Event(); self.output_done=threading.Event(); self.stderr_done=threading.Event()
        self.lease=store.create(binding,argv)
        store.update(self.lease,kind='acp_keeper',state='keeper_leased_before_backend_spawn',
                     provider_terminal_observed=False,consumer_delivery='unverified')
        self.path=store.job(self.lease['id']); self.segments=Segments(self.path/'output',store.owner)
        self.protocol=Protocol(self); self.tracker=Tracker(self.protocol,self.publish)
        self.child=None; self.receipt_confirmed=False

    def publish(self,state):
        with self.state_lock:
            self.store.update(self.lease,tracker=state,heartbeat_at=time.time())

    def unknown(self,reason):
        self.admitting=False
        try:self.tracker.unknown(reason)
        except (OSError,ValueError,RuntimeError):pass

    def retain(self,channel,data):
        # Reserve/quota backpressure occurs BEFORE a write. Never truncate or
        # kill accepted work; keep at most one bounded frame per reader in RAM.
        while True:
            with self.segments.lock:
                capacity=(self.segments.bytes+len(data)<=MAX_BYTES and self.segments.count<65536
                          and space(self.path)>=RESERVE+len(data))
            if capacity:break
            self.unknown('output_backpressure'); self.done.wait(.2)
        try:
            row=self.segments.append(channel,data)
            with self.state_lock:
                self.store.update(self.lease,output_segments=self.segments.count,
                                  output_bytes=self.segments.bytes,consumer_delivery='unverified')
            return row
        except (OSError,ValueError,RuntimeError):
            # A data/metadata write may have committed. NEVER repeat that write,
            # consume another frame, acknowledge delivery or force-kill work.
            self.io_uncertain=True; self.unknown('output_write_uncertain_no_retry')
            threading.Event().wait()

    def maybe_close_input(self):
        with self.tracker.lock:
            complete=not self.tracker.server_pending and all(x['completed'] for x in self.tracker.pending.values())
        if self.finish_requested and complete:
            with self.input_lock:
                if self.child.stdin and not self.child.stdin.closed:self.child.stdin.close()

    def backend_reader(self):
        try:
            while True:
                raw=self.child.stdout.readline(acp.MAX_FRAME+1)
                if not raw:break
                self.retain('stdout',raw)  # Durable before ANY client can read.
                if len(raw)>acp.MAX_FRAME or not raw.endswith(b'\n'):
                    self.unknown('oversized_or_incomplete_backend_frame')
                    while raw and not raw.endswith(b'\n'):
                        raw=self.child.stdout.readline(acp.MAX_FRAME+1)
                        if raw:self.retain('stdout',raw)
                    continue
                try:self.tracker.backend(json.loads(raw))
                except (OSError,ValueError,TypeError,RuntimeError):self.unknown('backend_tracking_unknown')
                self.maybe_close_input()
        except (OSError,ValueError,RuntimeError):self.unknown('backend_transport_unknown')
        finally:
            try:self.tracker.transport_closed()
            except (OSError,ValueError,RuntimeError):pass
            self.output_done.set()

    def stderr_reader(self):
        try:
            while raw:=self.child.stderr.read1(65536):self.retain('stderr',raw)
        except (OSError,ValueError,RuntimeError):self.unknown('stderr_transport_unknown')
        finally:self.stderr_done.set()

    def heartbeat(self):
        while not self.done.wait(15):
            try:
                self.tracker.heartbeat()
                with self.state_lock:self.store.update(self.lease,heartbeat_at=time.time())
            except (OSError,ValueError,RuntimeError):self.unknown('heartbeat_unknown')

    def input(self,message):
        if not self.receipt_confirmed or self.child.poll() is not None:
            return {'admitted':False,'error':'backend receipt unknown/exited; no new request or replay'}
        raw=(json.dumps(message,ensure_ascii=True,separators=(',',':'))+'\n').encode()
        shadow.require(len(raw)<=acp.MAX_FRAME,'input frame too large; not forwarded')
        forward,error=self.tracker.client(message,delivered=False)
        if not forward:return {'admitted':False,'response':error}
        try:
            with self.input_lock:
                remaining=memoryview(raw)
                while remaining:
                    count=self.child.stdin.write(remaining)
                    if not count:raise OSError('backend input unavailable')
                    remaining=remaining[count:]
                self.child.stdin.flush()
            self.tracker.client_output_delivered()
            return {'admitted':True,'outcome':'forwarded_once_NOT_provider_completion'}
        except (OSError,ValueError,RuntimeError):
            self.unknown('input_forward_outcome_uncertain')
            return {'admitted':None,'error':'forward outcome unknown; no replay; inspect output'}

    def handle(self,message):
        shadow.require(isinstance(message,dict),'unknown keeper request')
        if set(message)=={'op','frame'} and message['op']=='input':return self.input(message['frame'])
        if set(message)=={'op','sequence'} and message['op']=='read':
            try:return {'segment':Segments.read(self.path/'output',message['sequence'],self.store.owner)}
            except FileNotFoundError:return {'segment':None,'consumer_delivery':'unverified'}
        if message=={'op':'finish-input'}:
            self.admitting=False; self.finish_requested=True; self.maybe_close_input()
            return {'finish_requested':True,'existing_work_not_killed':True,'consumer_delivery':'unverified'}
        if message=={'op':'status'}:
            with self.state_lock:return {'session':self.lease,'all_work_idle':False,'termination_capable':False}
        raise RuntimeError('unsupported keeper action; no clear/replay/kill/ack API')

    def serve(self,argv,descriptor):
        work.subreaper()
        with self.state_lock:self.store.update(self.lease,state='backend_spawn_attempted')
        # argv is an isolated privilege-drop gate for the configured UID. No
        # shell/user-site/startup hook is evaluated before the session lease.
        # Socket/descriptor/parent-owned pipe custody precedes the native effect.
        # A lost Popen receipt must not close a live child's input/output pipes.
        listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        endpoint=self.path/'keeper.sock'; listener.bind(str(endpoint)); os.chmod(endpoint,0o600)
        listener.listen(4); listener.settimeout(.2)
        shadow.publish(Path(descriptor),{'schema':1,'session':self.lease['id'],'socket':str(endpoint),
                      'pid':os.getpid(),'pid_start':work.process_start(os.getpid()),'boot_id':self.binding['boot_id'],
                      'backend_spawn':'not_confirmed; inspect keeper status, never replay startup',
                      'consumer_delivery':'unverified','termination_capable':False},new=True)
        in_read,in_write=os.pipe(); out_read,out_write=os.pipe(); err_read,err_write=os.pipe()
        streams=[os.fdopen(in_write,'wb',buffering=0),os.fdopen(out_read,'rb',buffering=65536),os.fdopen(err_read,'rb',buffering=65536)]
        try:
            self.child=subprocess.Popen(argv,stdin=in_read,stdout=out_write,stderr=err_write,
                                        start_new_session=True,close_fds=True)
            self.receipt_confirmed=True
        except (OSError,ValueError,RuntimeError):
            self.child=UncertainChild(); self.unknown('backend_spawn_outcome_uncertain_no_retry')
        finally:
            for fd in [in_read,out_write,err_write]:os.close(fd)
        self.child.stdin,self.child.stdout,self.child.stderr=streams
        if self.receipt_confirmed:
            try:
                with self.state_lock:self.store.update(self.lease,backend_pid=self.child.pid,
                                                      backend_start=work.process_start(self.child.pid),
                                                      native_receipt_confirmed=True)
            except (OSError,ValueError,RuntimeError):self.unknown('backend_publication_unknown')
        threads=[threading.Thread(target=f,daemon=True) for f in [self.backend_reader,self.stderr_reader,self.heartbeat]]
        for thread in threads:thread.start()
        try:
            while True:
                if self.child.poll() is not None and self.output_done.is_set() and self.stderr_done.is_set():break
                try:connection,_=listener.accept()
                except socket.timeout:continue
                with connection:
                    credentials=connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12)
                    peer_pid,peer_uid,_=struct.unpack('3i',credentials)
                    if peer_uid!=0 or peer_pid<=0:
                        continue  # Rejected peer must NEVER abort existing backend work.
                    connection.settimeout(3)
                    with connection.makefile('rwb',buffering=0) as wire:
                        try:
                            raw=wire.readline(acp.MAX_FRAME+1)
                            shadow.require(raw.endswith(b'\n') and len(raw)<=acp.MAX_FRAME,'incomplete/oversized client message')
                            reply=self.handle(json.loads(raw))
                        except (OSError,ValueError,TypeError,RuntimeError) as error:
                            reply={'admitted':False,'error_type':type(error).__name__,'outcome':'unknown_or_rejected; never replay input'}
                        try:
                            remaining=memoryview((json.dumps(reply,separators=(',',':'))+'\n').encode())
                            while remaining:
                                count=wire.write(remaining)
                                if not count:raise OSError('custody client output closed')
                                remaining=remaining[count:]
                        except OSError:pass  # Lost ACK does NOT cancel work or permit replay.
            code=self.child.wait()
            for thread in threads[:2]:thread.join()
            work.wait_descendants()  # Includes detached/cross-signal descendants.
            with self.state_lock:
                self.store.update(self.lease,state='backend_and_local_children_reaped_output_pending',exit_status=code,
                                  consumer_delivery='unverified',output_delivery='unverified')
            return code if code>=0 else 128-code
        finally:
            self.done.set(); threads[2].join(); listener.close()
            for stream in [self.child.stdin,self.child.stdout,self.child.stderr]:
                if stream and not stream.closed:stream.close()
            # Retain socket descriptor/records/output. Never mark old custody idle.


def drop_command(backend,arguments,home,extra_env=None):
    user=pwd.getpwuid(1001); home=Path(home)
    st=home.stat(); shadow.require(stat.S_ISDIR(st.st_mode) and st.st_uid==1001 and not st.st_mode&0o022,'untrusted target home')
    environment={'HOME':str(home),'USER':user.pw_name,'LOGNAME':user.pw_name,'LANG':'C.UTF-8',
                 'PATH':'/run/current-system/sw/bin','XDG_RUNTIME_DIR':str(home/'.runtime'),
                 'AWS_EC2_METADATA_DISABLED':'true','KIRO_DISABLE_TELEMETRY':'true','KIRO_NO_AUTO_UPDATE':'1'}
    if extra_env:
        # Library-only private native fixture injection; CLI exposes no env override.
        environment.update(extra_env)
    gate=('import os,sys,json,ctypes;libc=ctypes.CDLL(None,use_errno=True);'
          'assert libc.prctl(38,1,0,0,0)==0;os.setgroups([]);os.setgid(int(sys.argv[1]));os.setuid(1001);'
          'environment=json.loads(sys.argv[2]);os.chdir(environment["HOME"]);'
          'os.execvpe(sys.argv[3],sys.argv[3:],environment)')
    return [sys.executable,'-B','-I','-c',gate,str(user.pw_gid),json.dumps(environment),str(backend),*arguments]


def settings(value):
    shadow.require(set(value)=={'schema','deployment_id','shadow_deployment_id','store_directory','backend','backend_sha256'}
                   and type(value['schema']) is int and value['schema']==1
                   and re.fullmatch('[0-9a-f]{12}',value['deployment_id'])
                   and re.fullmatch('[0-9a-f]{12}',value['shadow_deployment_id'])
                   and value['store_directory']==str(shadow.BASE/value['shadow_deployment_id'])
                   and value['backend'].startswith('/nix/store/') and value['backend'].endswith('/bin/kiro-cli-chat')
                   and re.fullmatch('[0-9a-f]{64}',value['backend_sha256']),'invalid warm ACP configuration')
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--descriptor',type=Path,required=True); parser.add_argument('--home',type=Path)
    parser.add_argument('arguments',nargs=argparse.REMAINDER); args=parser.parse_args()
    shadow.require(os.geteuid()==0,'root-owned keeper required')
    cfg=settings(shadow.read(args.config)); shadow.require(version(Path(__file__).parent)==cfg['deployment_id']
                    and shadow.version(Path(__file__).parent)==cfg['shadow_deployment_id'],'source version mismatch')
    shadow.require(not os.path.lexists(args.descriptor),'existing/uncertain session descriptor; never replay startup')
    shadow.require(binary(cfg['backend'])==cfg['backend_sha256'],'native bytes changed; no unverified fallback')
    store=shadow.Store(cfg['store_directory']); store.check(); binding=shadow.protected_observation()
    home=args.home or Path(pwd.getpwuid(1001).pw_dir)
    extra=args.arguments[1:] if args.arguments[:1]==['--'] else args.arguments
    native=[cfg['backend'],'acp',*extra]
    keeper=Keeper(store,binding,native,shadow.protected_observation)
    code=keeper.serve(drop_command(cfg['backend'],['acp',*extra],home),args.descriptor)
    sys.exit(code)


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError):
        print('Warm ACP keeper outcome unknown or admission refused; inspect custody; no replay',file=sys.stderr)
        sys.exit(75)
