// Pinned, in-memory vendor-store adapter. No prompts/IDs/transcripts cross RPC.
// This participant is ALWAYS unverified for whole-server release.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

export const BUNDLE_SHA256 = '67cec0aace08d9bef505ea135b908333edfb7e5ad049c3ffa678ed7bcb133384';
const KEY = Symbol.for('nixos.spot.kiro.frontend.v1');
const FACTORY = 'c={setState:i,getState:a,getInitialState:()=>s,subscribe:(l)=>{return t.add(l),()=>t.delete(l)}},s=n=e(i,a,c);return c';
const NEW = new Set(['handleUserInput', 'sendMessage', 'queueMessage', 'executeCommandWithArg',
  'replaceQueuedMessage', 'respondToApproval', 'setApprovalMode', 'confirmTrustAllTools',
  'confirmFirstLaunchUiMode', 'submitSurvey', 'terminateAllCrewSessions']);
const DRAFT = new Set(['insert', 'newline', 'setCommandInput', 'attachFile', 'addPendingImage',
  'setPendingFileAttachment', 'setVoicePartialText', 'setPendingVoiceText']);
const CONTINUE = new Set(['processQueue', 'processMessageStream', 'cancelMessage', 'clearSteerMessage',
  'clearQueue', 'removeQueuedMessage', 'clearInput', 'clearCommandInput', 'removeAttachedFile',
  'clearAttachedFiles', 'removePendingImage', 'clearPendingImages', 'backspace', 'delete',
  'cancelApproval', 'handleCompactionEvent']);

export function census(state, actions = 0) {
  if (!state || typeof state.isInitialized !== 'boolean' || typeof state.isProcessing !== 'boolean'
      || typeof state.isCompacting !== 'boolean' || !Array.isArray(state.queuedMessages)
      || !state.queuedMessages.every(x => typeof x === 'string')
      || !state.input || !Array.isArray(state.input.lines)
      || !state.input.lines.every(x => typeof x === 'string')
      || typeof state.commandInputValue !== 'string'
      || !Array.isArray(state.pendingImages) || !Array.isArray(state.attachedFiles)
      || !Array.isArray(state.approvalQueue)) throw Error('Frontend state contract changed');
  if (state.pendingSteerContent !== null && typeof state.pendingSteerContent !== 'string')
    throw Error('Frontend steering contract changed');
  return {
    initialized: state.isInitialized,
    queued: state.queuedMessages.length,
    pending_steer: state.pendingSteerContent !== null,
    processing: state.isProcessing || state.isCompacting || state.currentAbortController != null
      || state.cancelInProgress != null || state._activeStreamHandler != null
      || state.pendingApproval != null || state.approvalQueue.length > 0,
    actions,
    draft: state.input.lines.some(x => x.length > 0) || state.commandInputValue.length > 0
      || state.pendingImages.length > 0 || state.attachedFiles.length > 0
      || state.pendingFileAttachment != null || state.pendingVoiceText != null || state.voicePartialText != null
      || state.queuedInputRestore != null,
  };
}
const hasWork = x => !x.initialized || x.queued > 0 || x.pending_steer || x.processing || x.actions > 0 || x.draft;
const snapshotKey = x => JSON.stringify(x); // Six primitive fields ONLY, never the store.

export class LocalCustody {
  constructor(rpc, schedule = queueMicrotask) {
    this.rpc = rpc; this.schedule = schedule;
    this.store = null; this.active = true; this.healthy = true;
    this.actions = 0; this.continuations = 0; this.scheduled = false;
    this.last = null; this.attached = false; this.rejections = 0;
  }
  fault() {
    if (this.healthy) {
      this.healthy = false;
      try { this.rpc('fault'); } catch {} // Existing epoch/participant stays sticky.
    }
  }
  deny(fn) {
    this.rejections++;
    this.store?.getState().showTransientAlert({message: 'Shutdown admission closed; input not accepted', status: 'error', autoHideMs: 3000});
    // Match the vendor's void UI-action shape, not a backend acceptance ACK.
    return fn.constructor.name === 'AsyncFunction' ? Promise.resolve() : undefined;
  }
  admit() {
    if (!this.healthy) return false;
    try {
      if (!this.rpc('admit').accepted) return false;
      this.active = true; return true;
    } catch { this.fault(); return false; }
  }
  continuation(fn, ...args) {
    if (!this.active) { this.fault(); throw Error('Frontend continuation lost custody'); }
    this.continuations++;
    try { return fn(...args); } finally { this.continuations--; }
  }
  later() {
    if (this.scheduled) return;
    this.scheduled = true;
    this.schedule(() => { this.scheduled = false; this.sync(); });
  }
  sync(proposed = undefined) {
    if (!this.healthy || !this.store) return;
    try {
      const value = census(proposed ?? this.store.getState(), this.actions);
      const key = snapshotKey(value);
      if (key === this.last) return;
      const result = this.rpc('state', value);
      if (!result.accepted) { this.fault(); return; }
      this.active = hasWork(value); this.last = key;
    } catch { this.fault(); }
  }
  set(original, get, update, replace) {
    const before = get();
    // Preserve the exact pinned vanilla-store semantics, including one and
    // only one invocation of functional updaters. Other stores pass through.
    if (!before || !Object.hasOwn(before, 'queuedMessages')) return original(update, replace);
    const patch = typeof update === 'function' ? update(before) : update;
    if (Object.is(patch, before)) return;
    const replacing = replace ?? (typeof patch !== 'object' || patch === null);
    const after = replacing ? patch : Object.assign({}, before, patch);
    try {
      const value = census(after, this.actions);
      if (!this.active && hasWork(value)) this.sync(after); // custody BEFORE mutation
    } catch { this.fault(); }
    // A malformed callback/IPC loss must NOT truncate already admitted output.
    original(patch, replace);
    this.later();
  }
  wrap(name, fn) {
    const owner = this;
    return function (...args) {
      const continuing = owner.continuations > 0;
      const needAdmission = !continuing && (NEW.has(name) || (DRAFT.has(name) && !owner.active));
      if (needAdmission && !owner.admit()) return owner.deny(fn);
      if (continuing && !owner.active) { owner.fault(); return owner.deny(fn); }
      let tracked = true;
      try { tracked = needAdmission || owner.active || hasWork(census(owner.store.getState(), owner.actions)); }
      catch { owner.fault(); }
      if (!tracked) return fn.apply(this, args); // empty processQueue/display-only cancellation
      owner.actions++; owner.sync();
      let result;
      const finish = () => { owner.actions--; owner.later(); };
      try { result = fn.apply(this, args); }
      catch (error) { finish(); throw error; }
      if (result && typeof result.then === 'function') result.then(finish, finish);
      else finish();
      return result;
    };
  }
  attach(store) {
    const value = store.getState();
    if (!value || !Object.hasOwn(value, 'queuedMessages')) return;
    if (this.attached) { this.fault(); throw Error('Duplicate frontend store'); }
    census(value);
    for (const name of ['handleUserInput', 'sendMessage', 'queueMessage', 'processQueue', 'showTransientAlert'])
      if (typeof value[name] !== 'function') throw Error('Frontend action contract changed');
    this.store = store; this.attached = true;
    for (const name of [...NEW, ...DRAFT, ...CONTINUE]) {
      if (typeof value[name] !== 'function') { this.fault(); throw Error('Frontend action contract changed'); }
      value[name] = this.wrap(name, value[name]);
    }
    this.sync();
  }
  close() {
    try {
      if (this.healthy && this.store && !hasWork(census(this.store.getState(), this.actions))) this.rpc('close');
      else this.fault();
    } catch { this.fault(); }
  }
}

export function instrumentSource(source, expectedHash = BUNDLE_SHA256) {
  if (createHash('sha256').update(source).digest('hex') !== expectedHash) throw Error('Pinned frontend bundle changed; refusing fallback');
  if (source.split(FACTORY).length !== 2) throw Error('Frontend store factory changed');
  const key = `globalThis[Symbol.for('nixos.spot.kiro.frontend.v1')]`;
  const factory = `_spot=${key},c={setState:(...x)=>_spot.set(i,a,...x),getState:a,getInitialState:()=>s,subscribe:(l)=>{return t.add(l),()=>t.delete(l)}},s=n=e(c.setState,a,c);_spot.attach(c);return c`;
  let patched = source.replace(FACTORY, factory);
  const start = patched.indexOf('processQueue:async()=>{');
  const end = patched.indexOf('},clearQueue:', start);
  if (start < 0 || end < start) throw Error('Frontend queue continuation contract changed');
  let queue = patched.slice(start, end);
  if (queue.split('c().sendMessage(').length !== 3 || queue.split('c().handleUserInput(').length !== 2)
    throw Error('Frontend queue handoff contract changed');
  queue = queue.replaceAll('c().sendMessage(', `${key}.continuation(c().sendMessage,`)
    .replaceAll('c().handleUserInput(', `${key}.continuation(c().handleUserInput,`);
  return patched.slice(0, start) + queue + patched.slice(end);
}

export function cliRPC(tool, startup, run = spawnSync) {
  let id; let seq = 0;
  const call = (action, value) => {
    const payload = action === 'attach' ? {startup} : {id, seq: seq + 1, ...(action === 'state' ? {counters: value} : {})};
    const result = run(tool, [action], {input: JSON.stringify(payload), encoding: 'utf8', maxBuffer: 4096});
    if (result.error || result.status !== 0) throw Error('Frontend custody unavailable');
    const reply = JSON.parse(result.stdout);
    if (!reply || reply.accepted !== true && reply.accepted !== false || !Number.isSafeInteger(reply.seq))
      throw Error('Frontend custody reply unknown');
    if (action === 'attach') {
      if (typeof reply.id !== 'string' || !/^frontend-[0-9a-f]{32}$/.test(reply.id) || reply.seq !== 0 || !reply.accepted)
        throw Error('Frontend attachment refused');
      id = reply.id;
    } else if (reply.seq !== seq + 1 && action !== 'fault') throw Error('Frontend custody sequence changed');
    seq = reply.seq; return reply;
  };
  call('attach');
  return call;
}

export function installFrontend(tool) {
  if (!globalThis.Bun || !process.env.SPOT_KIRO_STARTUP || globalThis[KEY]) throw Error('Frontend bootstrap unavailable');
  const rpc = cliRPC(tool, process.env.SPOT_KIRO_STARTUP);
  delete process.env.SPOT_KIRO_STARTUP; // Do not give backend/tools bootstrap custody.
  const custody = new LocalCustody(rpc);
  globalThis[KEY] = custody;
  Bun.plugin({name: 'spot-pinned-frontend-custody', setup(build) {
    build.onLoad({filter: /tui[.]js$/}, args => ({contents: instrumentSource(readFileSync(args.path, 'utf8')), loader: 'js'}));
  }});
  const timer = setInterval(() => { try { rpc('heartbeat'); } catch { custody.fault(); } }, 15000);
  timer.unref();
  process.once('exit', () => { clearInterval(timer); custody.close(); });
  return custody;
}
