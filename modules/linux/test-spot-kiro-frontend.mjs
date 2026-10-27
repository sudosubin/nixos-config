import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {LocalCustody, census, cliRPC, instrumentSource} from './spot-kiro-frontend.mjs';

const names = 'handleUserInput sendMessage queueMessage executeCommandWithArg replaceQueuedMessage respondToApproval setApprovalMode confirmTrustAllTools confirmFirstLaunchUiMode submitSurvey terminateAllCrewSessions insert newline setCommandInput attachFile addPendingImage setPendingFileAttachment setVoicePartialText setPendingVoiceText processQueue processMessageStream cancelMessage clearSteerMessage clearQueue removeQueuedMessage clearInput clearCommandInput removeAttachedFile clearAttachedFiles removePendingImage clearPendingImages backspace delete cancelApproval handleCompactionEvent'.split(' ');
function fixture(overrides={}) {
  const frames=[];const tasks=[];let open=true;
  const rpc=(action,value)=>{frames.push([action,value]);return {accepted: action!=='admit'||open};};
  const core=new LocalCustody(rpc,fn=>tasks.push(fn));
  let state={isInitialized:true,isProcessing:false,isCompacting:false,queuedMessages:[],pendingSteerContent:null,
    input:{lines:['']},commandInputValue:'',pendingImages:[],attachedFiles:[],approvalQueue:[],pendingApproval:null,
    currentAbortController:null,cancelInProgress:null,_activeStreamHandler:null,showTransientAlert:()=>{}};
  for(const name of names)state[name]=()=>{};
  const raw=(value,replace)=>{const p=typeof value==='function'?value(state):value;state=replace?p:Object.assign({},state,p);};
  const store={getState:()=>state,setState:(value,replace)=>core.set(raw,()=>state,value,replace)};
  Object.assign(state,overrides(store,core,frames));core.attach(store);
  return {core,store,frames,tasks,setOpen:value=>{open=value},flush:()=>{while(tasks.length)tasks.shift()();}};
}
const defaults=()=>({});

test('census contains primitive counters, not input/IDs/text',()=>{
 const f=fixture(defaults);f.store.setState({input:{lines:['PRIVATE_DRAFT']},queuedMessages:['PRIVATE_PROMPT']});
 const x=census(f.store.getState());assert.equal(x.draft,true);assert.equal(x.queued,1);
 assert(!JSON.stringify(x).includes('PRIVATE'));assert.deepEqual(Object.keys(x).sort(),['actions','draft','initialized','pending_steer','processing','queued']);
});
test('queued acceptance occurs only after synchronous admission acknowledgement',()=>{
 const f=fixture((store,core,frames)=>({queueMessage(text){
  assert(frames.findLastIndex(([action])=>action==='admit')>=0);
  assert.equal(frames.at(-1)[0],'state');assert.equal(frames.at(-1)[1].actions,1);
  assert.equal(store.getState().queuedMessages.length,0);
  store.setState({queuedMessages:[text]});
 }}));
 f.store.getState().queueMessage('PRIVATE_PROMPT');f.flush();assert.equal(f.core.active,true);assert.equal(census(f.store.getState()).queued,1);
});
test('new submission is rejected even while an old frontend epoch is held',()=>{
 let ran=0;let alerts=0;
 const f=fixture((store)=>({queueMessage(){ran++},showTransientAlert(){alerts++}}));
 f.store.setState({isProcessing:true});f.flush();f.setOpen(false);
 f.store.getState().queueMessage('never-accepted');assert.equal(ran,0);assert.equal(alerts,1);assert.equal(f.core.active,true);
});
test('queue pop then send in same turn never releases custody',()=>{
 const f=fixture(defaults);f.store.setState({queuedMessages:['queued']});f.flush();f.frames.length=0;
 f.store.setState({queuedMessages:[]});f.store.setState({isProcessing:true});
 assert(!f.frames.some(([a,v])=>a==='state'&&v&&!v.processing&&!v.queued));f.flush();assert.equal(f.core.active,true);
});
test('pending async producer prevents local-idle release',async()=>{
 let finish;
 const f=fixture(()=>({sendMessage:async()=>new Promise(resolve=>{finish=resolve})}));
 const p=f.store.getState().sendMessage('private');f.flush();assert.equal(f.core.active,true);assert.equal(f.core.actions,1);
 finish();await p;await Promise.resolve();f.flush();assert.equal(f.core.actions,0);assert.equal(f.core.active,false);
});
test('explicit same-stack continuation retains existing custody behind a fault fence',()=>{
 const f=fixture(store=>({sendMessage(){store.setState({isProcessing:true})}}));
 f.store.setState({queuedMessages:['queued']});f.flush();f.setOpen(false);
 const before=f.frames.filter(([a])=>a==='admit').length;
 f.core.continuation(f.store.getState().sendMessage,'private');f.flush();assert.equal(f.core.active,true);
 assert.equal(f.frames.filter(([a])=>a==='admit').length,before);
});
test('draft update acquires custody before mutating the store',()=>{
 const f=fixture(defaults);let beforeMutation;
 f.core.rpc=(a,v)=>{if(a==='state'&&v.draft)beforeMutation=f.store.getState().input.lines[0];return {accepted:true};};
 f.store.setState({input:{lines:['private']}});assert.equal(beforeMutation,'');assert.equal(f.core.active,true);
});
test('stream chunks with unchanged primitive state do not spawn repeated CLI calls',()=>{
 const f=fixture(defaults);f.store.setState({isProcessing:true});f.flush();f.frames.length=0;
 for(let i=0;i<100;i++){f.store.setState({streamingContent:'fixture-chunk-'+i});f.flush();}
 assert.equal(f.frames.length,0);
});
test('functional updater runs exactly once',()=>{
 const f=fixture(defaults);let count=0;
 f.store.setState(s=>{count++;return {...s,commandInputValue:'draft'}});assert.equal(count,1);
});
test('malformed state or lost IPC preserves vendor updates but stays unknown',()=>{
 const f=fixture(defaults);f.store.setState({queuedMessages:'new schema'});f.flush();
 assert.equal(f.store.getState().queuedMessages,'new schema');assert.equal(f.core.healthy,false);
 const before=f.core.active;f.core.close();assert.equal(f.core.active,before);
});
test('failed admission does not invoke producer or store private arguments in metadata',()=>{
 const f=fixture(()=>({handleUserInput:async()=>{throw Error('must not run')}}));f.setOpen(false);
 f.store.getState().handleUserInput('PRIVATE_PROMPT');assert(!JSON.stringify(f.frames).includes('PRIVATE_PROMPT'));
});
test('quiescent close differs from busy exit',()=>{
 const a=fixture(defaults);a.core.close();assert.equal(a.frames.at(-1)[0],'close');
 const b=fixture(defaults);b.store.setState({pendingSteerContent:'private'});b.flush();b.core.close();assert.equal(b.frames.at(-1)[0],'fault');
});
test('CLI uses only opaque IDs and counters with strict reply sequences',()=>{
 let n=0;const calls=[];
 const rpc=cliRPC('/fixture/tool','job-'+'a'.repeat(32),(tool,args,opts)=>{
  calls.push(JSON.parse(opts.input));return {status:0,stdout:JSON.stringify(n++===0?{id:'frontend-'+'b'.repeat(32),seq:0,accepted:true}:{seq:1,accepted:true})};
 });
 rpc('state',{initialized:true,queued:0,pending_steer:false,processing:false,actions:0,draft:false});
 assert.deepEqual(Object.keys(calls[1]).sort(),['counters','id','seq']);
});
test('changed bundle is rejected rather than falling back to uninstrumented UI',()=>{
 assert.throws(()=>instrumentSource('changed'),/bundle changed/);
});
test('exact pinned source patch covers all queue handoffs without changing disk files',()=>{
 const factory='c={setState:i,getState:a,getInitialState:()=>s,subscribe:(l)=>{return t.add(l),()=>t.delete(l)}},s=n=e(i,a,c);return c';
 const source=factory+';processQueue:async()=>{await c().sendMessage(a);await c().sendMessage(b);await c().handleUserInput(c)},clearQueue:';
 const hash=createHash('sha256').update(source).digest('hex');const out=instrumentSource(source,hash);
 assert(out.includes('_spot.attach(c)'));assert.equal(out.split('.continuation(').length,4);
 assert(!source.includes('_spot.attach'));
});
