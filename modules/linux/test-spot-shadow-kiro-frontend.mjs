import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {ParseObserver,shadowRPC,instrumentWarmSource} from './spot-shadow-kiro-frontend.mjs';
const sha=x=>createHash('sha256').update(x).digest('hex');
function observer(){const frames=[],tasks=[];let faults=0;const core=new ParseObserver((a,v)=>{frames.push([a,v]);return {accepted:true}},()=>faults++,fn=>tasks.push(fn));return {core,frames,tasks,get faults(){return faults},flush(){while(tasks.length)tasks.shift()()}};}

test('parse receipt strips transport tag but preserves all vendor content',()=>{
 const f=observer();const msg={jsonrpc:'2.0',id:1,result:{text:'PRIVATE_OUTPUT'},__nixosShadowFrame:{sequence:3,sha256:'a'.repeat(64)}};
 assert.deepEqual(f.core.parsed(msg),{jsonrpc:'2.0',id:1,result:{text:'PRIVATE_OUTPUT'}});
 f.flush();assert(!JSON.stringify(f.frames).includes('PRIVATE_OUTPUT'));assert.equal(f.frames[0][0],'parsed');
 assert.equal(f.frames[0][1].sequence,3);assert.equal(f.frames[0][1].count,1);
});
test('many output frames coalesce into one content-free prefix watermark',()=>{
 const f=observer();let chain=sha('');
 for(let n=0;n<100;n++){const digest=sha('output-'+n);chain=sha(chain+':'+(n*2)+':'+digest);f.core.parsed({result:n,__nixosShadowFrame:{sequence:n*2,sha256:digest}})}
 assert.equal(f.frames.length,0);assert.equal(f.tasks.length,1);f.flush();assert.equal(f.frames.length,1);
 assert.deepEqual(f.frames[0][1],{sequence:198,chain,count:100});
});
test('unbound or regressed output faults without truncating native response',()=>{
 const f=observer();assert.deepEqual(f.core.parsed({result:'kept'}),{result:'kept'});assert.equal(f.faults,1);
 const g=observer();g.core.parsed({result:1,__nixosShadowFrame:{sequence:1,sha256:'a'.repeat(64)}});
 assert.deepEqual(g.core.parsed({result:2,__nixosShadowFrame:{sequence:1,sha256:'a'.repeat(64)}}),{result:2});assert.equal(g.faults,1);
});
test('RPC failure keeps already parsed output while marking custody unknown',()=>{
 let failed=0;const p=new ParseObserver(()=>{throw Error('lost')},()=>failed++,()=>{});
 assert.deepEqual(p.parsed({result:'preserved',__nixosShadowFrame:{sequence:0,sha256:'a'.repeat(64)}}),{result:'preserved'});
 p.flush();assert.equal(failed,1);assert.equal(p.healthy,false);
});
test('parse receipt never claims UI delivery, idle, ready or releases a lease',()=>{
 const f=observer();f.core.parsed({result:1,__nixosShadowFrame:{sequence:0,sha256:'a'.repeat(64)}});f.flush();
 assert.deepEqual(Object.keys(f.frames[0][1]).sort(),['chain','count','sequence']);
 assert(!JSON.stringify(f.frames).includes('delivered'));assert(!JSON.stringify(f.frames).includes('ready'));
});
test('shadow CLI preserves one shared sequence for counters and parse receipts',()=>{
 const frames=[];let count=0;const rpc=shadowRPC('/immutable/client','job-'+'a'.repeat(32),(tool,args,opts)=>{
  frames.push([args[0],JSON.parse(opts.input)]);return {status:0,stdout:JSON.stringify(count++?{seq:count-1,accepted:true}:{id:'frontend-'+'b'.repeat(32),seq:0,accepted:true})};
 });
 rpc('parsed',{sequence:9,chain:'c'.repeat(64),count:2});rpc('heartbeat');
 assert.equal(frames[1][1].seq,1);assert.equal(frames[2][1].seq,2);assert(!JSON.stringify(frames).includes('PRIVATE'));
});
test('lost sequence/reply is not retried or silently reset',()=>{
 let n=0;const rpc=shadowRPC('/immutable/client','job-'+'a'.repeat(32),()=>({status:0,stdout:JSON.stringify(n++?{seq:99,accepted:true}:{id:'frontend-'+'b'.repeat(32),seq:0,accepted:true})}));
 assert.throws(()=>rpc('heartbeat'),/sequence changed/);assert.equal(n,2);
});
test('changed vendor bundle is rejected before uninstrumented fallback',()=>{assert.throws(()=>instrumentWarmSource('changed'),/bundle changed/)});
const factory='c={setState:i,getState:a,getInitialState:()=>s,subscribe:(l)=>{return t.add(l),()=>t.delete(l)}},s=n=e(i,a,c);return c';
const queue=';processQueue:async()=>{await c().sendMessage(a);await c().sendMessage(b);await c().handleUserInput(c)},clearQueue:';
const pipe='function ofe(e){let{stdin:n,stdout:t}=e;o.enqueue(JSON.parse(b));o.enqueue(JSON.parse(a.trim()))}function cfe(e){return e}';
test('pinned patch retains queue handoffs and both complete/EOF parse hooks',()=>{
 const src=factory+queue+pipe;const out=instrumentWarmSource(src,sha(src));assert(out.includes('_spot.attach(c)'));
 assert.equal(out.split('.continuation(').length,4);assert.equal(out.split('.parsed(JSON.parse(').length,3);
 assert(!src.includes('_spot.attach'));assert(!src.includes('.parsed(JSON.parse('));
});
test('missing or duplicate pipe parser cannot silently drop receipts',()=>{
 const src=factory+queue;assert.throws(()=>instrumentWarmSource(src,sha(src)),/pipe adapter changed/);
 const bad=factory+queue+pipe.replace('o.enqueue(JSON.parse(b))','o.enqueue(JSON.parse(b));o.enqueue(JSON.parse(b))');
 assert.throws(()=>instrumentWarmSource(bad,sha(bad)),/parse contract changed/);
});
