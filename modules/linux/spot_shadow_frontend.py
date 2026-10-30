#!/usr/bin/env python3
"""Process-bound SHADOW TUI counter/parse receipts; NEVER delivery/idle authority.

For explicitly launched NEW, pinned Bun frontends only. No canonical Protocol,
startup-ready, output ACK, clear/takeover or existing-session retrofit. Prompt,
RPC IDs and user content are not persisted in frontend metadata.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import struct
import sys
import threading
import time
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).parent))
import spot_shadow as shadow
import spot_frontend as frontend
import spot_work as work

BUN_SHA='67892bb6734ef352f90a964f0a2a680d5f6e6d15bdb5510e56b8065ac4d599ae'
BUNDLE_SHA='67cec0aace08d9bef505ea135b908333edfb7e5ad049c3ffa678ed7bcb133384'


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while data:=stream.read(65536):h.update(data)
    return h.hexdigest()


def actor(pid,ancestor,entry,cgroup):
    shadow.require(type(pid) is int and pid>1 and work.process_uid(pid)==1001
                   and frontend.descendant(pid,ancestor),'unowned frontend actor')
    start=work.process_start(pid)
    shadow.require(Path('/proc/'+str(pid)+'/cgroup').read_text().strip()=='0::'+cgroup,
                   'frontend actor outside owned workload')
    shadow.require(Path('/proc/'+str(pid)+'/ns/pid').stat().st_ino==Path('/proc/self/ns/pid').stat().st_ino,
                   'frontend PID namespace differs')
    argv=Path('/proc/'+str(pid)+'/cmdline').read_bytes().split(bytes([0]))
    shadow.require(str(entry).encode() in argv and digest('/proc/'+str(pid)+'/exe')==BUN_SHA,
                   'frontend executable/immutable entry differs')
    shadow.require(work.process_start(pid)==start,'frontend identity changed during binding')
    return {'pid':pid,'pid_start':start,'uid':1001,'pid_namespace':os.readlink('/proc/'+str(pid)+'/ns/pid'),
            'cgroup':cgroup,'bun_sha256':BUN_SHA,'entry':str(entry)}


class Census:
    def __init__(self,store,binding,startup,protection):
        self.store,self.binding,self.startup,self.protection=store,binding,startup,protection
        self.lock=threading.RLock();self.owner=None;self.offered={};self.chains={};self.parsed_count=0
        self.chain=hashlib.sha256(b'').hexdigest()
        self.ident='frontend-'+startup['id'][4:]
        self.record=None

    def attach(self,value,owner):
        with self.lock:
            shadow.require(value=={'startup':self.startup['id']} and self.owner is None,
                           'frontend already attached/unknown startup; no takeover')
            shadow.require(self.protection()==self.binding,'frontend protection epoch changed')
            self.owner=dict(owner)
            self.record=self.store.create(self.binding,['pinned Bun frontend counters; content omitted'])
            self.store.update(self.record,kind='shadow_kiro_frontend',parent_startup=self.startup['id'],
                              frontend_id=self.ident,actor=self.owner,seq=0,healthy=True,initialized=False,
                              state='frontend_initializing_unverified',admission_rejections=0,
                              parsed_output_count=0,output_delivery='unverified')
            return {'id':self.ident,'seq':0,'accepted':True}

    def invoke(self,action,value,owner):
        with self.lock:
            shadow.require(self.owner==owner and self.record is not None,'frontend actor unknown; no rebind')
            expected={'id','seq','counters'} if action=='state' else {'id','seq','output'} if action=='parsed' else {'id','seq'}
            shadow.require(isinstance(value,dict) and set(value)==expected and value['id']==self.ident
                           and type(value['seq']) is int
                           and (value['seq']==self.record['seq']+1 or action=='fault' and value['seq']==self.record['seq']),
                           'frontend sequence/owner changed; inspect, no replay')
            changes={'seq':value['seq'],'heartbeat_at':time.time()};accepted=True
            if action=='admit':
                try:accepted=self.record['healthy'] is True and self.protection()==self.binding
                except (OSError,ValueError,RuntimeError):accepted=False
                if not accepted:changes['admission_rejections']=self.record['admission_rejections']+1
                changes['state']='frontend_new_input_observed_unverified' if accepted else 'frontend_new_input_rejected'
            elif action=='state':
                values=frontend.counters(value['counters'])
                changes.update(counters=values,initialized=values['initialized'],
                               state='frontend_local_work_unverified' if frontend.busy(values) else 'frontend_local_quiescent_NOT_idle')
            elif action=='heartbeat':pass
            elif action=='fault':changes.update(healthy=False,state='frontend_fault_unknown')
            elif action=='close':
                values=self.record.get('counters')
                shadow.require(self.record['healthy'] and values and not frontend.busy(values),
                               'frontend exit has unresolved custody')
                changes['state']='frontend_closed_locally_output_pending'
            elif action=='parsed':
                receipt=value['output'];shadow.require(isinstance(receipt,dict) and set(receipt)=={'sequence','chain','count'}
                   and type(receipt['sequence']) is int and receipt['sequence'] in self.chains
                   and type(receipt['count']) is int and receipt['count']>=self.parsed_count
                   and self.chains[receipt['sequence']]==(receipt['count'],receipt['chain']),
                   'unoffered/regressed/tampered parsed-output watermark')
                self.parsed_count=receipt['count'];changes.update(parsed_output_count=self.parsed_count,
                    parsed_output_watermark=receipt,parsed_output_stage='JSON_parsed_before_dispatch_NOT_UI_delivery')
            else:raise RuntimeError('unknown frontend action; no clear/ack/takeover API')
            self.store.update(self.record,**changes)
            return {'seq':value['seq'],'accepted':accepted}

    def offer(self,row):
        with self.lock:
            shadow.require(row.get('channel')=='stdout' and type(row.get('sequence')) is int
                           and re.fullmatch('[0-9a-f]{64}',row.get('sha256','')),
                           'unknown output offering')
            sequence=row['sequence']
            shadow.require(sequence not in self.offered or self.offered[sequence]==row['sha256'],
                           'output sequence changed')
            if sequence not in self.offered:
                shadow.require(not self.offered or sequence>max(self.offered),'output offering out of order')
                self.chain=hashlib.sha256((self.chain+':'+str(sequence)+':'+row['sha256']).encode()).hexdigest()
                self.offered[sequence]=row['sha256'];self.chains[sequence]=(len(self.offered),self.chain)


def client(endpoint,action,value):
    # Short-lived UID1001 Python-I client. Root broker validates SO_PEERCRED and
    # its real Bun parent, not caller-supplied PID/environment/labels.
    shadow.require(action in {'attach','admit','state','heartbeat','fault','close','parsed'},'unknown frontend client operation')
    request={'op':'frontend','action':action,'value':value}
    raw=(json.dumps(request,separators=(',',':'))+'\n').encode();shadow.require(len(raw)<=4096,'frontend frame exceeds bound')
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
        connection.settimeout(5);connection.connect(str(endpoint));connection.sendall(raw)
        with connection.makefile('rb') as stream:
            data=stream.readline(4097);shadow.require(len(data)<=4096 and data.endswith(b'\n'),'frontend response truncated')
            result=json.loads(data)
    shadow.require(isinstance(result,dict) and type(result.get('accepted')) is bool
                   and type(result.get('seq')) is int,'frontend custody outcome unknown; no automatic retry')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['attach','admit','state','heartbeat','fault','close','parsed'])
    args=parser.parse_args();endpoint=os.environ.get('SPOT_SHADOW_TUI_ENDPOINT')
    shadow.require(endpoint and Path(endpoint).is_absolute() and os.geteuid()==1001,'explicit UID1001 frontend endpoint required')
    raw=sys.stdin.buffer.read(4097);shadow.require(len(raw)<=4096,'frontend metadata exceeds bound')
    value=json.loads(raw);print(json.dumps(client(endpoint,args.action,value),separators=(',',':')))


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError):
        print('Shadow frontend custody unavailable; no new input acknowledged',file=sys.stderr);sys.exit(75)
