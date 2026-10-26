// Local-only control RPC, executed as the workload UID. No credential arguments,
// raw exceptions, model calls, config mutation, or interrupting drain policies.
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

try {
  const [vendor, method, rawParams, expectedBoot = ''] = process.argv.slice(2);
  const allowed = new Set(['status', 'system.info', 'gateway.suspend.prepare',
    'gateway.suspend.status', 'gateway.suspend.resume', 'gateway.suspend.handoff']);
  if (!allowed.has(method)) throw Error('unsupported control method');
  const params = JSON.parse(rawParams);
  if (method === 'gateway.suspend.prepare' &&
      (params.drain !== false || params.terminalPolicy !== 'preserve')) throw Error('unsafe drain policy');
  const hashes = {
    'gateway-suspend-coordinator-CvUFNpPI.mjs': 'f0f050c3c4bf73f2c2f6138cbef2ffa39f96b4c52c95c5a979ef2e1188cd47df',
    'suspend-B8VOsoYU.mjs': '9d830ff2e1a7412894781686c2b6790766ab674de83a6ce2deb1de3a70a36f3d',
    'gateway-active-work-O1dcRiAF.mjs': '87c0e7710a3b103f0908ea1d0aa3059116cf6522f9c9e20bca87c3e2869c6c59',
  };
  for (const [name, digest] of Object.entries(hashes)) {
    if (createHash('sha256').update(await readFile(join(vendor, name))).digest('hex') !== digest) {
      throw Error('unverified gateway lifecycle contract');
    }
  }
  const load = name => import(pathToFileURL(join(vendor, name)).href);
  const { a: context } = await load('restart-health-probe-BQiOZUUA.mjs');
  const { p: portFor } = await load('update-command-service-plan-DQpd4cuw.mjs');
  const { i: call, y: authFor } = await load('call-DQXZ8pIa.mjs');
  const { t: probeFor } = await load('local-http-probe-Cz2TMKGP.mjs');
  const { config, auth } = await context(process.env);
  const port = await portFor({ config, serviceEnv: process.env });
  const target = await probeFor(config).resolveWebSocketTarget(port);
  const url = new URL(target.url);
  if (!['ws:', 'wss:'].includes(url.protocol) || !['127.0.0.1', '[::1]'].includes(url.hostname)) {
    throw Error('only an explicit loopback gateway is permitted');
  }
  const controlAuth = await authFor({ auth, authNone: config.gateway?.auth?.mode === 'none', env: process.env });
  let bootId;
  const result = await call({ method, params, config, ...controlAuth,
    serviceTargetUrl: target.url, localPortOverride: port, ignoreEnvUrlOverride: true,
    tlsFingerprint: target.tlsFingerprint, timeoutMs: 8000,
    onHelloOk: hello => { bootId = hello.server.bootId; },
    assertDispatchCurrent: () => {
      if (typeof bootId !== 'string' || !bootId || (expectedBoot && bootId !== expectedBoot)) {
        throw Error('gateway connection identity changed');
      }
    },
  });
  let value = result;
  if (method === 'status') value = { pid: result.pid, runtimeVersion: result.runtimeVersion, shutdownBudget: result.shutdownBudget };
  if (method === 'system.info') value = { pid: result.pid, processInstanceId: result.processInstanceId };
  process.stdout.write(JSON.stringify({ boot_id: bootId, result: value }) + '\n');
} catch {
  // A vendor exception can include sensitive config/auth. Never forward it.
  process.stderr.write('Local gateway control unavailable; no safe outcome established\n');
  process.exitCode = 75;
}
