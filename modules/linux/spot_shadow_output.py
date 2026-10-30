#!/usr/bin/env python3
"""Bounded private output for NEW shadow native helpers, never delivery authority.

Parent-owned pipes precede spawn. Quota/storage pressure stops reading, never
truncates or kills accepted work. An uncertain immutable write is NOT retried.
This is local custody only; no retirement, takeover, replay or idle API.
"""
import base64
import os
from pathlib import Path
import threading
import time
import sys
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).parent))
import spot_shadow as shadow
import spot_shadow_acp as acp

CHUNK=65536
BRIDGE_BYTES=1024**2


class Output:
    def __init__(self,store,lease):
        self.store,self.lease=store,lease
        self.lock=threading.RLock()
        self.segments=acp.Segments(store.job(lease['id'])/'output',store.owner)
        self.readers=[];self.pressure=False;self.uncertain=False
        self.update(output_format='immutable_segments_v1',output_complete=False,
                    output_segments=0,output_bytes=0,consumer_delivery='unverified')

    def update(self,**changes):
        with self.lock:self.store.update(self.lease,**changes)

    def unknown(self,reason):
        try:self.update(state=reason,heartbeat_at=time.time(),consumer_delivery='unverified')
        except (OSError,ValueError,RuntimeError):pass  # Original lease remains unknown.

    def hold(self):
        # Never close the read pipe or consume another chunk after an uncertain
        # write: either could destroy accepted work. No automatic retry/reset.
        threading.Event().wait()

    def retain(self,channel,data):
        while True:
            # Capacity and append share the SAME lock across stdout and stderr.
            with self.segments.lock:
                capacity=(self.segments.bytes+len(data)<=acp.MAX_BYTES and self.segments.count<65536
                          and acp.space(self.segments.directory)>=acp.RESERVE+len(data))
                if capacity:
                    try:
                        row=self.segments.append(channel,data,visible=False)
                        self.update(output_segments=self.segments.count,output_bytes=self.segments.bytes)
                        self.segments.expose(row['sequence'])
                        return row
                    except (OSError,ValueError,RuntimeError):
                        self.uncertain=True;self.unknown('helper_output_write_uncertain_no_retry')
                        self.hold()
                        raise RuntimeError('uncertain helper output cannot resume')
            self.pressure=True;self.unknown('helper_output_backpressure')
            time.sleep(.2)

    def reader(self,channel,stream):
        try:
            while data:=stream.read1(CHUNK):self.retain(channel,data)
        except (OSError,ValueError,RuntimeError):
            self.uncertain=True;self.unknown('helper_output_read_uncertain_no_retry');self.hold()
            return
        stream.close()  # Only confirmed EOF closes a read side.

    def start(self,streams):
        shadow.require(not self.readers,'helper readers already started; no replay')
        for channel,stream in streams.items():
            thread=threading.Thread(target=self.reader,args=(channel,stream),daemon=True)
            self.readers.append(thread);thread.start()

    def finish(self):
        for thread in self.readers:thread.join()
        shadow.require(not self.uncertain,'helper output uncertain; no completion')
        self.update(output_complete=True,output_segments=self.segments.count,output_bytes=self.segments.bytes)


def bridge_output(store,ident):
    """Bounded verified body for the bound actor, NOT consumer delivery/ACK."""
    path=store.job(ident);record=shadow.read(path/'record.json',store.owner)
    shadow.require(record.get('output_format')=='immutable_segments_v1'
                   and record.get('output_complete') is True
                   and type(record.get('output_segments')) is int
                   and 0<=record['output_segments']<=65536,'helper output incomplete; retained, not replayed')
    bodies={'stdout':bytearray(),'stderr':bytearray()};total=0
    for number in range(record['output_segments']):
        row=acp.Segments.read(path/'output',number,store.owner)
        data=base64.b64decode(row['data_base64'],validate=True);total+=len(data)
        shadow.require(total<=BRIDGE_BYTES,'helper output exceeds bridge bound; retained, NOT truncated')
        bodies[row['channel']].extend(data)
    shadow.require(total==record.get('output_bytes'),'helper output receipt changed; no replay')
    return {channel:base64.b64encode(body).decode() for channel,body in bodies.items()}
