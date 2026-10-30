#!/usr/bin/env python3
"""New shadow TUI bridge: pinned Bun actor + keeper IPC, not idle authority.

Only root-launched NEW actor descendants may call it. Existing TUI/Herdr stay
untouched. Parse receipts deliberately do NOT certify UI delivery or readiness.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import threading
import time
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).parent))
import spot_shadow as shadow
import spot_shadow_frontend as front
import spot_shadow_acp as acp
import spot_work as work


def rpc(endpoint,message,limit=2*1024**2):
    raw=(json.dumps(message,separators=(',',':'))+'\n').encode()
    shadow.require(len(raw)<=acp.acp.MAX_FRAME,'bridge request exceeds bound')
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
        connection.settimeout(8);connection.connect(str(endpoint));connection.sendall(raw)
        with connection.makefile('rb') as stream:data=stream.readline(limit+1)
    shadow.require(len(data)<=limit and data.endswith(b'\n'),'bridge reply unknown/truncated; never replay input')
    value=json.loads(data);shadow.require(isinstance(value,dict),'unknown bridge response')
    return value


def opaque_run(store,binding,backend,arguments,home,native_env=None):
    """Dedicated wrapper only: explicit owned HOME, never host-home fallback."""
    shadow.require(acp.space(store.root)>=acp.RESERVE,'native helper spool reserve insufficient; no effect')
    command=acp.drop_command(backend,arguments,home,native_env)
    adapter=shadow.Adapter(store,binding,[backend,*arguments]);saved=adapter.create
    original=[os.dup(n) for n in [0,1,2]];opened=[]
    def create(kind):
        lease=saved(kind);path=store.job(lease['id'])
        for number,name in [(1,'stdout'),(2,'stderr')]:
            fd=os.open(path/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            opened.append(fd);os.dup2(fd,number)
        return lease
    adapter.create=create
    try:
        null=os.open('/dev/null',os.O_RDONLY)
        try:os.dup2(null,0)
        finally:os.close(null)
        code=work.run_job(adapter,command)
        for fd in opened:os.fsync(fd)
    finally:
        for n,fd in zip([0,1,2],original):os.dup2(fd,n);os.close(fd)
        for fd in opened:os.close(fd)
    lease=adapter.lease;store.update(lease,exit_status=code,kind='tui_opaque_native_helper',
        output_spool={name:shadow.spool_hash(store.job(lease['id'])/name) for name in ['stdout','stderr']})
    return {'job':lease['id'],'exit_status':code,'output_delivery':'unverified'}


class Broker:
    def __init__(self,store,binding,startup,keeper_descriptor,entry,cgroup,home,backend,public_client,native_env=None):
        self.store,self.binding,self.startup=store,binding,startup
        self.keeper=keeper_descriptor;self.entry=Path(entry);self.cgroup=cgroup
        self.home,self.backend=str(home),str(backend)
        shadow.require(isinstance(public_client,dict) and set(public_client)=={'frontend','proxy'},'explicit client roles required')
        self.public_clients={role:str(path) for role,path in public_client.items()}
        self.native_env=native_env
        self.census=front.Census(store,binding,startup,shadow.protected_observation)
        self.ancestor=None;self.actor=None;self.proxy=None;self.lock=threading.RLock()
        self.done=threading.Event();self.active=threading.BoundedSemaphore(8)
        self.listener=None;self.endpoint=None

    def check_parent(self,peer_pid,attach=False,role='frontend'):
        shadow.require(type(peer_pid) is int and peer_pid>1 and work.process_uid(peer_pid)==1001,
                       'untrusted bridge caller')
        peer_start=work.process_start(peer_pid)
        peer_group=Path('/proc/'+str(peer_pid)+'/cgroup').read_text().strip()
        shadow.require(peer_group=='0::'+self.cgroup,'bridge caller escaped owned workload')
        # Client Python must be root-owned immutable source, not a PID supplied
        # by the caller. The real OS parent is the pinned Bun actor.
        argv=Path('/proc/'+str(peer_pid)+'/cmdline').read_bytes().split(bytes([0]))
        program=self.public_clients[role]
        shadow.require(len(argv)>=3 and argv[:3]==[sys.executable.encode(),b'-I',program.encode()],
                       'unknown frontend client program/isolated interpreter')
        parent=int(Path('/proc/'+str(peer_pid)+'/stat').read_text().rsplit(')',1)[1].split()[1])
        if attach:
            shadow.require(self.ancestor is not None,'frontend native launcher not bound')
            owner=front.actor(parent,self.ancestor,self.entry,self.cgroup)
        else:
            owner=self.actor;shadow.require(owner is not None and parent==owner['pid']
                    and work.process_start(parent)==owner['pid_start'] and work.process_uid(parent)==1001
                    and str(self.entry).encode() in Path('/proc/'+str(parent)+'/cmdline').read_bytes().split(bytes([0])),
                    'frontend parent/source changed; no takeover')
        shadow.require(work.process_start(peer_pid)==peer_start,'bridge client identity changed')
        return owner

    def keeper_rpc(self,message):
        shadow.require(work.process_start(self.keeper['pid'])==self.keeper['pid_start'],
                       'keeper owner changed; no session replay/takeover')
        return rpc(self.keeper['socket'],message)

    def handle(self,peer_pid,message):
        shadow.require(isinstance(message,dict),'invalid UI bridge request')
        op=message.get('op')
        if op=='frontend':
            shadow.require(set(message)=={'op','action','value'},'invalid frontend frame')
            with self.lock:
                attaching=message['action']=='attach';owner=self.check_parent(peer_pid,attaching)
                if attaching:
                    result=self.census.attach(message['value'],owner);self.actor=owner
                else:result=self.census.invoke(message['action'],message['value'],owner)
                return result
        if op in {'acp-input','acp-read','native-once'}:
            owner=self.check_parent(peer_pid,role='proxy')
            if op.startswith('acp-'):
                with self.lock:
                    identity=(peer_pid,work.process_start(peer_pid))
                    shadow.require(self.proxy is None or self.proxy==identity,'ACP proxy changed; no automatic reconnect/replay')
                    self.proxy=identity
                if op=='acp-input':
                    shadow.require(set(message)=={'op','frame'},'invalid ACP input')
                    result=self.keeper_rpc({'op':'input','frame':message['frame']})
                    return result
                shadow.require(set(message)=={'op','sequence'},'invalid ACP read')
                result=self.keeper_rpc({'op':'read','sequence':message['sequence']});row=result.get('segment')
                if row:
                    body=base64.b64decode(row['data_base64']);shadow.require(len(body)==row['bytes']
                            and hashlib.sha256(body).hexdigest()==row['sha256'],'keeper output body mismatch')
                    if row['channel']=='stdout':self.census.offer(row)
                return result
            shadow.require(set(message)=={'op','arguments'} and isinstance(message['arguments'],list)
                           and message['arguments'] and len(message['arguments'])<=64
                           and all(isinstance(x,str) and '\x00' not in x and len(x)<=8192 for x in message['arguments'])
                           and message['arguments'][0]!='acp','invalid non-ACP native route')
            # A separate leased wrapper owns every opaque native helper. Never
            # redirect process-global FDs from this multi-client broker thread.
            program=('from pathlib import Path;import sys,json;sys.path.insert(0,'+repr(str(Path(__file__).parent))+');'
                     'import spot_shadow_ui as u;'
                     'value=u.opaque_run(u.shadow.Store('+repr(str(self.store.root))+'),u.shadow.protected_observation(),'
                     +repr(self.backend)+','+repr(message['arguments'])+','+repr(self.home)+','+repr(self.native_env)+');print(json.dumps(value))')
            result=subprocess.run([sys.executable,'-B','-I','-c',program],capture_output=True,text=True)
            shadow.require(result.returncode==0,'native helper outcome unknown; inspect custody; never replay')
            record=json.loads(result.stdout);path=self.store.job(record['job'])
            response={'exit_status':record['exit_status'],'output_delivery':'unverified'}
            for channel in ['stdout','stderr']:
                with (path/channel).open('rb') as stream:data=stream.read(1024**2+1)
                shadow.require(len(data)<=1024**2,'native helper output exceeds bridge bound; retained, not truncated')
                response[channel]=base64.b64encode(data).decode()
            return response
        raise RuntimeError('unknown UI bridge action; no ACK/clear/takeover')

    def open(self,endpoint):
        endpoint=Path(endpoint);shadow.require(not os.path.lexists(endpoint),'existing bridge endpoint; no replay')
        self.listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.listener.bind(str(endpoint))
        os.chown(endpoint,0,__import__('pwd').getpwuid(1001).pw_gid);os.chmod(endpoint,0o660)
        self.listener.listen(8);self.listener.settimeout(.2);self.endpoint=str(endpoint)

    def serve(self):
        while not self.done.is_set():
            try:connection,_=self.listener.accept()
            except socket.timeout:continue
            except OSError:
                if self.done.is_set():break
                raise
            if not self.active.acquire(blocking=False):connection.close();continue
            thread=threading.Thread(target=self.connection,args=(connection,),daemon=True);thread.start()

    def connection(self,connection):
        try:
            with connection:
                peer_pid,uid,_=struct.unpack('3i',connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                if uid!=1001:return
                connection.settimeout(10)
                with connection.makefile('rwb',buffering=0) as wire:
                    try:
                        raw=wire.readline(acp.acp.MAX_FRAME+1);shadow.require(raw.endswith(b'\n') and len(raw)<=acp.acp.MAX_FRAME,'incomplete bridge frame')
                        result=self.handle(peer_pid,json.loads(raw))
                    except (OSError,ValueError,TypeError,RuntimeError):result={'accepted':False,'error':'UI custody unknown; no automatic input replay'}
                    data=memoryview((json.dumps(result,separators=(',',':'))+'\n').encode())
                    try:
                        while data:
                            n=wire.write(data)
                            if not n:break
                            data=data[n:]
                    except OSError:pass
        finally:self.active.release()

    def close(self):
        self.done.set()
        if self.listener:self.listener.close()
        # Keep participant/startup/native jobs, socket and output as unknown.


def proxy(endpoint,arguments):
    if arguments[:1]!=['acp']:
        value=rpc(endpoint,{'op':'native-once','arguments':arguments})
        shadow.require('exit_status' in value,'native helper admission unavailable')
        for channel,stream in [('stdout',sys.stdout.buffer),('stderr',sys.stderr.buffer)]:
            stream.write(base64.b64decode(value[channel]));stream.flush()
        return value['exit_status']
    closed=threading.Event();fault=[]
    def send():
        try:
            while raw:=sys.stdin.buffer.readline(acp.acp.MAX_FRAME+1):
                shadow.require(raw.endswith(b'\n') and len(raw)<=acp.acp.MAX_FRAME,'invalid ACP input; not forwarded')
                frame=json.loads(raw);reply=rpc(endpoint,{'op':'acp-input','frame':frame})
                if reply.get('admitted') is False and reply.get('response'):
                    sys.stdout.buffer.write((json.dumps(reply['response'])+'\n').encode());sys.stdout.buffer.flush()
                elif reply.get('admitted') is not True:
                    raise RuntimeError('ACP forward outcome unknown; never replay')
        except (OSError,ValueError,RuntimeError) as error:fault.append(type(error).__name__)
        finally:closed.set()
    thread=threading.Thread(target=send,daemon=True);thread.start();sequence=0
    while not closed.is_set():
        reply=rpc(endpoint,{'op':'acp-read','sequence':sequence});row=reply.get('segment')
        if row is None:time.sleep(.02);continue
        sequence+=1;data=base64.b64decode(row['data_base64'])
        shadow.require(len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],'bad output segment')
        if row['channel']=='stdout':
            value=json.loads(data)
            shadow.require(isinstance(value,dict) and '__nixosShadowFrame' not in value,'unrecognized vendor output transport')
            value['__nixosShadowFrame']={'sequence':row['sequence'],'sha256':row['sha256']}
            sys.stdout.buffer.write((json.dumps(value,separators=(',',':'))+'\n').encode());sys.stdout.buffer.flush()
        else:sys.stderr.buffer.write(data);sys.stderr.buffer.flush()
    # Client EOF/crash NEVER asks keeper to terminate accepted work. End of the
    # explicit TUI actor is reconciled separately; no resume/input replay here.
    return 75 if fault else 0


def main():
    endpoint=os.environ.get('SPOT_SHADOW_TUI_ENDPOINT');shadow.require(endpoint and os.geteuid()==1001,'explicit UI actor endpoint required')
    sys.exit(proxy(endpoint,sys.argv[1:]))


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError):
        print('Shadow UI proxy outcome unknown; no automatic input replay',file=sys.stderr);sys.exit(75)
