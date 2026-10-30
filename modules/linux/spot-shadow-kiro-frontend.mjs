// Explicit NEW shadow TUI only. Parse watermarks are NOT UI delivery or idle.
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {LocalCustody, instrumentSource, BUNDLE_SHA256} from './spot-kiro-frontend.mjs';

const FRONT = Symbol.for('nixos.spot.kiro.frontend.v1');
const OUTPUT = Symbol.for('nixos.spot.kiro.shadow.output.v1');
const hash = value => createHash('sha256').update(value).digest('hex');

export function shadowRPC(tool, startup, run=spawnSync) {
  let id;let seq=0;
  const rpc=(action,value)=>{
    const payload=action==='attach'?{startup}:{id,seq:seq+1,
      ...(action==='state'?{counters:value}:action==='parsed'?{output:value}:{})};
    const response=run(tool,[action],{input:JSON.stringify(payload),encoding:'utf8',maxBuffer:4096});
    if(response.error||response.status!==0)throw Error('Shadow frontend custody unavailable; no new input acknowledged');
    const reply=JSON.parse(response.stdout);
    if(!reply||typeof reply.accepted!=='boolean'||!Number.isSafeInteger(reply.seq))throw Error('Shadow frontend reply unknown');
    if(action==='attach'){
      if(!/^frontend-[0-9a-f]{32}$/.test(reply.id)||reply.seq!==0||!reply.accepted)throw Error('Shadow frontend attach refused');
      id=reply.id;
    }else if(reply.seq!==seq+1&&action!=='fault')throw Error('Shadow frontend sequence changed');
    seq=reply.seq;return reply;
  };
  rpc('attach');return rpc;
}

export class ParseObserver {
  constructor(rpc,fault,schedule=fn=>setTimeout(fn,250)) {
    this.rpc=rpc;this.fault=fault;this.schedule=schedule;
    this.count=0;this.chain=hash('');this.sequence=-1;this.pending=false;this.healthy=true;
  }
  parsed(message) {
    if(!message||typeof message!=='object') {this.bad();return message;}
    const {__nixosShadowFrame:receipt,...native}=message;
    try {
      if(!receipt||!Number.isSafeInteger(receipt.sequence)||receipt.sequence<=this.sequence
         ||typeof receipt.sha256!=='string'||!/^[0-9a-f]{64}$/.test(receipt.sha256))throw Error('Unknown offered output');
      this.chain=hash(this.chain+':'+receipt.sequence+':'+receipt.sha256);
      this.count++;this.sequence=receipt.sequence;
      if(!this.pending){this.pending=true;this.schedule(()=>this.flush());}
    }catch{this.bad();}
    // A custody fault NEVER truncates or alters already received native output.
    // Strip only our explicit transport tag before the vendor RPC dispatcher.
    return native;
  }
  bad(){if(this.healthy){this.healthy=false;this.fault();}}
  flush(){
    if(!this.pending)return;this.pending=false;
    if(!this.healthy)return;
    try{
      const result=this.rpc('parsed',{sequence:this.sequence,chain:this.chain,count:this.count});
      if(!result.accepted)throw Error('Parse watermark rejected');
    }catch{this.bad();}
  }
}

export function instrumentWarmSource(source,expectedHash=BUNDLE_SHA256) {
  let patched=instrumentSource(source,expectedHash);
  const start=patched.indexOf('function ofe(e){let{stdin:n,stdout:t}=e;');
  const end=patched.indexOf('function cfe(e){',start);
  if(start<0||end<start)throw Error('Pinned ACP pipe adapter changed; refusing fallback');
  let pipe=patched.slice(start,end);
  const key="globalThis[Symbol.for('nixos.spot.kiro.shadow.output.v1')]";
  for(const [old,next] of [
    ['o.enqueue(JSON.parse(b))',`o.enqueue(${key}.parsed(JSON.parse(b)))`],
    ['o.enqueue(JSON.parse(a.trim()))',`o.enqueue(${key}.parsed(JSON.parse(a.trim())))`],
  ]){
    if(pipe.split(old).length!==2)throw Error('Pinned ACP parse contract changed');
    pipe=pipe.replace(old,next);
  }
  return patched.slice(0,start)+pipe+patched.slice(end);
}

export function installWarmFrontend(tool) {
  if(!globalThis.Bun||!process.env.SPOT_KIRO_STARTUP||!process.env.SPOT_SHADOW_TUI_ENDPOINT
     ||globalThis[FRONT]||globalThis[OUTPUT])throw Error('Explicit shadow frontend bootstrap unavailable');
  const rpc=shadowRPC(tool,process.env.SPOT_KIRO_STARTUP);
  delete process.env.SPOT_KIRO_STARTUP;
  const custody=new LocalCustody(rpc);
  const output=new ParseObserver(rpc,()=>custody.fault());
  globalThis[FRONT]=custody;globalThis[OUTPUT]=output;
  Bun.plugin({name:'spot-shadow-pinned-frontend',setup(build){
    build.onLoad({filter:/tui[.]js$/},args=>({contents:instrumentWarmSource(readFileSync(args.path,'utf8')),loader:'js'}));
  }});
  const timer=setInterval(()=>{try{output.flush();rpc('heartbeat');}catch{custody.fault();}},15000);
  timer.unref();
  process.once('exit',()=>{clearInterval(timer);output.flush();custody.close();});
  return {custody,output};
}
