#!/usr/bin/env python3
"""ACP stdio admission proxy. Never records prompts, sessions, RPC IDs, or replies.

Only a recognized terminal response completes a prompt lease. Cancellation,
acknowledgement, EOF, errors and missing heartbeats are not evidence of idle.
"""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import uuid

import spot_work as work

MAX_FRAME = 1024 * 1024
STOP_REASONS = {'end_turn', 'max_tokens', 'max_turn_requests', 'refusal', 'cancelled'}
# These methods have request-scoped, rather than acknowledged asynchronous,
# semantics in the pinned Kiro/ACP contract. Unknown extensions fail closed.
REQUEST_SCOPED = {'initialize', 'authenticate', 'session/new', 'session/load',
                  'session/list', 'session/set_mode', 'session/set_model',
                  'session/set_config_option', '_kiro.dev/commands/options',
                  '_kiro.dev/settings/list', '_kiro.dev/session/list'}
CONTROL_NOTIFICATIONS = {'session/cancel', 'notifications/initialized', 'initialized', '_session/terminate'}
WORK_UPDATES = {'agent_message_chunk', 'agent_thought_chunk', 'user_message_chunk',
                'tool_call', 'tool_call_update', 'plan'}
METADATA_UPDATES = {'available_commands_update', 'current_mode_update',
                    'config_option_update', 'session_info_update', 'usage_update'}


def kiro_metadata(method, params):
    """Pinned v2 notification shapes observed with the real native backend.

    These are declarations/metrics, never idle authority. Nonempty subagent or
    tool/MCP inventories remain unknown until their separate custody is proven.
    Participants still independently block whole-server release.
    """
    if not isinstance(params, dict):
        return False
    if method == '_kiro.dev/subagent/list_update':
        return (set(params) == {'subagents', 'pendingStages'}
                and params['subagents'] == [] and params['pendingStages'] == [])
    session = params.get('sessionId')
    if not isinstance(session, str) or not 0 < len(session) <= 256:
        return False
    if method in {'_kiro.dev/mcp/governance_disabled', '_kiro.dev/webTools/governance_disabled'}:
        return set(params) == {'sessionId', 'apiFailure'} and type(params['apiFailure']) is bool
    if method == '_kiro.dev/commands/available':
        return (set(params) == {'sessionId', 'commands', 'prompts', 'tools', 'mcpServers'}
                and all(params[key] == [] for key in ('prompts', 'tools', 'mcpServers'))
                and isinstance(params['commands'], list)
                and all(isinstance(c, dict) and set(c) <= {'name', 'description', 'meta'}
                        and isinstance(c.get('name'), str) and isinstance(c.get('description'), str)
                        and ('meta' not in c or isinstance(c['meta'], dict))
                        for c in params['commands']))
    if method == '_kiro.dev/metadata':
        if not {'sessionId'} < set(params) <= {'sessionId', 'contextUsagePercentage', 'turnDurationMs'}:
            return False
        return (('contextUsagePercentage' not in params
                 or (type(params['contextUsagePercentage']) in (int, float)
                     and 0 <= params['contextUsagePercentage'] <= 100
                     and math.isfinite(params['contextUsagePercentage'])))
                and ('turnDurationMs' not in params
                     or (type(params['turnDurationMs']) is int and params['turnDurationMs'] >= 0)))
    return False


def rpc_id(value):
    if type(value) is int and abs(value) <= 2**53:
        return ('number', value)
    if isinstance(value, str) and 0 < len(value) <= 256:
        return ('string', value)
    raise ValueError('invalid RPC identifier')


def error_response(ident, code, message):
    return {'jsonrpc': '2.0', 'id': ident, 'error': {'code': code, 'message': message}}


class Tracker:
    def __init__(self, protocol, publish=lambda state: None):
        self.protocol = protocol
        self.publish = publish
        self.lock = threading.RLock()
        self.pending = {}
        self.server_pending = set()
        self.server_delivered = set()
        self.backend_deliveries = set()
        self.initialized = False
        self.healthy = True
        self.closing = False
        self.unknown_lease = None
        self.admission_rejections = 0
        self.reason = 'initializing'

    def state(self):
        # Deliberately excludes method parameters, request/session IDs and text.
        return {'initialized': self.initialized, 'healthy': self.healthy and not self.closing,
                'active_requests': len(self.pending), 'server_requests': len(self.server_pending),
                'admission_rejections': self.admission_rejections,
                'reason': 'backend_output_closed' if self.closing and self.healthy else self.reason}

    def unknown(self, reason):
        self.healthy = False
        self.reason = reason
        if self.unknown_lease is None:
            try:
                self.unknown_lease = self.protocol.create('job')
            except (OSError, ValueError, RuntimeError):
                pass  # Unhealthy participant remains an independent blocker.
        self.publish(self.state())

    def client(self, message, delivered=True):
        """Return (forward, local_error). A denied request is NEVER forwarded."""
        with self.lock:
            if not isinstance(message, dict) or message.get('jsonrpc') != '2.0':
                self.unknown('invalid_client_frame')
                return False, error_response(None, -32600, 'Invalid ACP frame; request not started')
            method = message.get('method')
            if method is None:
                try:
                    ident = rpc_id(message.get('id'))
                    if ident not in self.server_pending or ('result' in message) == ('error' in message):
                        raise ValueError('unexpected client response')
                except ValueError:
                    self.unknown('unmatched_client_response')
                    return False, error_response(None, -32600, 'Unexpected ACP response')
                if delivered:
                    self.server_pending.remove(ident)
                    self.finish_completed()
                else:
                    self.server_delivered.add(ident)
                self.publish(self.state())
                return True, None
            if not isinstance(method, str):
                self.unknown('invalid_client_method')
                return False, error_response(None, -32600, 'Invalid ACP method')
            if 'id' not in message:
                if method in CONTROL_NOTIFICATIONS:
                    # Existing work may still be cancelled while admission is
                    # fenced; this never releases its pending prompt lease.
                    return True, None
                self.unknown('unknown_client_notification')
                return False, error_response(None, -32600, 'Untracked ACP notification not forwarded')
            try:
                ident = rpc_id(message['id'])
            except ValueError:
                self.unknown('invalid_client_id')
                return False, error_response(None, -32600, 'Invalid ACP request identifier')
            if ident in self.pending:
                self.unknown('duplicate_client_id')
                return False, error_response(message['id'], -32600, 'Duplicate ACP request identifier')
            if self.closing or not self.healthy or (not self.initialized and method != 'initialize'):
                return False, error_response(message['id'], -32074, 'ACP tracking is unknown; request not started')
            try:
                lease = self.protocol.create('job')
            except (OSError, ValueError, RuntimeError):
                # A count, not request contents or an idle claim. It makes
                # masked frontend errors distinguishable from accepted work.
                self.admission_rejections += 1
                self.publish(self.state())
                return False, error_response(message['id'], -32074, 'Shutdown admission closed; request not started')
            self.pending[ident] = {'method': method, 'lease': lease, 'completed': False, 'response_delivered': False}
            self.reason = 'requests_active'
            self.publish(self.state())
            return True, None

    def finish_completed(self):
        if self.server_pending:
            return
        for ident, entry in list(self.pending.items()):
            if entry['completed'] and entry['response_delivered']:
                self.protocol.remove(entry['lease']['id'], job_finished=True)
                del self.pending[ident]
        if self.healthy:
            self.reason = 'requests_active' if self.pending else 'idle'

    def client_output_delivered(self):
        with self.lock:
            self.server_pending.difference_update(self.server_delivered)
            self.server_delivered.clear()
            self.finish_completed()
            self.publish(self.state())

    def backend_output_delivered(self):
        with self.lock:
            for ident in self.backend_deliveries:
                if ident in self.pending:
                    self.pending[ident]['response_delivered'] = True
            self.backend_deliveries.clear()
            self.finish_completed()
            self.publish(self.state())

    def backend(self, message, delivered=True):
        # Backend bytes are always relayed, even when tracking becomes unknown.
        # Unknown data must not destroy output or interrupt existing work.
        with self.lock:
            if not isinstance(message, dict) or message.get('jsonrpc') != '2.0':
                self.unknown('invalid_backend_frame'); return
            if 'method' in message:
                if not isinstance(message['method'], str):
                    self.unknown('invalid_backend_method'); return
                if 'id' in message:
                    try:
                        ident = rpc_id(message['id'])
                        if ident in self.server_pending or not self.pending:
                            raise ValueError('unsolicited backend request')
                        self.server_pending.add(ident)
                    except ValueError:
                        self.unknown('untracked_backend_request'); return
                else:
                    params = message.get('params')
                    update = params.get('update') if isinstance(params, dict) else None
                    kind = update.get('sessionUpdate') if isinstance(update, dict) else None
                    if message['method'] != 'session/update':
                        if not kiro_metadata(message['method'], params):
                            self.unknown('unknown_backend_notification'); return
                    elif not isinstance(kind, str) or kind not in WORK_UPDATES | METADATA_UPDATES:
                        self.unknown('unknown_backend_notification'); return
                    if kind in WORK_UPDATES and not self.pending:
                        self.unknown('unsolicited_work_update'); return
                self.publish(self.state()); return
            try:
                ident = rpc_id(message.get('id'))
                entry = self.pending[ident]
            except (ValueError, KeyError):
                self.unknown('unmatched_backend_response'); return
            if ('result' in message) == ('error' in message) or 'error' in message:
                self.unknown('backend_error_or_invalid_response'); return
            result = message['result']
            method = entry['method']
            if method == 'initialize':
                if (not isinstance(result, dict) or type(result.get('protocolVersion')) is not int
                        or not isinstance(result.get('agentCapabilities'), dict)):
                    self.unknown('unknown_initialize_contract'); return
                self.initialized = True
            elif method == 'session/prompt':
                if (not isinstance(result, dict) or not isinstance(result.get('stopReason'), str)
                        or result['stopReason'] not in STOP_REASONS):
                    self.unknown('prompt_response_not_terminal'); return
            elif method not in REQUEST_SCOPED:
                # Async extensions (message/send, session/steer, custom command
                # execution) need their own proven completion contract.
                self.unknown('unknown_method_completion'); return
            entry['completed'] = True
            entry['response_delivered'] = delivered
            if not delivered:
                self.backend_deliveries.add(ident)
            if delivered:
                self.finish_completed()
            self.publish(self.state())

    def heartbeat(self):
        with self.lock:
            for entry in self.pending.values():
                self.protocol.heartbeat(entry['lease'])
            if self.unknown_lease is not None:
                self.protocol.heartbeat(self.unknown_lease)
            self.publish(self.state())

    def transport_closed(self):
        with self.lock:
            self.closing = True
            self.publish(self.state())

    def backend_exit(self, code=0):
        with self.lock:
            if code != 0 or self.pending or self.server_pending or not self.healthy:
                self.unknown('backend_exited_with_unknown_work')
                return False
            return True


class Participant:
    def __init__(self, protocol, backend):
        self.protocol = protocol
        self.ident = 'acp-' + uuid.uuid4().hex
        self.path = protocol.runtime / 'participants' / self.ident
        info = self.path.parent.lstat()
        if not self.path.parent.is_dir() or info.st_uid != protocol.root_uid:
            raise ValueError('ACP participant registry is not initialized')
        self.identity = {'schema': 1, 'id': self.ident, 'kind': 'acp', 'uid': os.geteuid(),
                         'boot_id': protocol.boot_id, 'pid': os.getpid(),
                         'pid_start': work.process_start(os.getpid()),
                         'backend_pid': backend.pid, 'backend_start': work.process_start(backend.pid)}

    def publish(self, state):
        with self.protocol.locked():
            self.protocol.publish(self.path, {**self.identity, **state, 'updated_at': time.time()})

    def remove(self):
        with self.protocol.locked():
            self.path.unlink()


def read_frame(stream):
    line = stream.readline(MAX_FRAME + 1)
    if not line:
        return None
    if len(line) > MAX_FRAME or not line.endswith(b'\n'):
        raise ValueError('ACP frame exceeds limit or is incomplete')
    return line


def bridge(protocol, argv):
    # Fail before spawning anything if root has not initialized admission.
    with protocol.locked():
        directory = protocol.runtime / 'participants'
        info = directory.lstat()
        if directory.is_symlink() or not directory.is_dir() or info.st_uid != protocol.root_uid:
            raise ValueError('ACP participant registry is not initialized')
    child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=None, bufsize=65536)
    participant = Participant(protocol, child)
    tracker = Tracker(protocol, participant.publish)
    participant.publish(tracker.state())
    output_lock = threading.Lock()
    input_lock = threading.Lock()
    done = threading.Event()
    client_closed = threading.Event()
    output_closed = threading.Event()

    def unknown(reason):
        with tracker.lock:
            try:
                tracker.unknown(reason)
            except (OSError, ValueError, RuntimeError):
                # The in-memory tracker is already unhealthy. A failed disk
                # publication stays stale/unknown, never permission to release.
                pass

    def maybe_close_input():
        with tracker.lock:
            complete = not tracker.server_pending and all(x['completed'] for x in tracker.pending.values())
        if client_closed.is_set() and complete:
            # EOF is not a cancellation or a deadline. Let every existing
            # request finish before closing the backend's input stream.
            with input_lock:
                try: child.stdin.close()
                except OSError: pass

    def output(raw):
        if output_closed.is_set():
            return False
        try:
            with output_lock:
                sys.stdout.buffer.write(raw)
                sys.stdout.buffer.flush()
            return True
        except OSError:
            output_closed.set()
            client_closed.set()
            unknown('client_output_closed')
            # Keep draining the backend after a frontend crash. Do not kill
            # existing work merely because nobody can consume its stdout.
            maybe_close_input()
            return False

    def client_reader():
        try:
            while True:
                raw = sys.stdin.buffer.readline(MAX_FRAME + 1)
                if not raw: break
                if len(raw) > MAX_FRAME or not raw.endswith(b'\n'):
                    unknown('oversized_or_truncated_client_frame')
                    while raw and not raw.endswith(b'\n'):
                        raw = sys.stdin.buffer.readline(MAX_FRAME + 1)
                    output(json.dumps(error_response(None, -32600, 'Invalid ACP frame; request not started')).encode()+b'\n')
                    continue
                try:
                    message = json.loads(raw)
                except (ValueError, UnicodeError):
                    unknown('invalid_client_json')
                    output(json.dumps(error_response(None, -32600, 'Invalid ACP JSON; request not started')).encode()+b'\n')
                    continue
                forward, error = tracker.client(message, delivered=False)
                if forward:
                    with input_lock:
                        remaining = memoryview(raw)
                        while remaining:
                            count = child.stdin.write(remaining)
                            if not count: raise OSError('backend input closed')
                            remaining = remaining[count:]
                        child.stdin.flush()
                    tracker.client_output_delivered()
                elif error is not None:
                    output(json.dumps(error, separators=(',', ':')).encode()+b'\n')
        except (OSError, ValueError, RuntimeError, TypeError):
            unknown('client_transport_error')
        finally:
            client_closed.set()
            maybe_close_input()

    def backend_reader():
        try:
            while True:
                raw = child.stdout.readline(MAX_FRAME + 1)
                if not raw: break
                if len(raw) > MAX_FRAME or not raw.endswith(b'\n'):
                    unknown('oversized_backend_frame')
                    # Never truncate an existing response. Stay unknown and
                    # stream the remainder without retaining it in memory.
                    output(raw)
                    while raw and not raw.endswith(b'\n'):
                        raw = child.stdout.readline(MAX_FRAME+1)
                        output(raw)
                    continue
                try:
                    tracker.backend(json.loads(raw), delivered=False)
                except (ValueError, UnicodeError, TypeError, OSError, RuntimeError):
                    unknown('invalid_backend_json_or_tracking_error')
                if output(raw):
                    tracker.backend_output_delivered()
                maybe_close_input()
        except (OSError, ValueError, RuntimeError, TypeError):
            unknown('backend_transport_error')
        finally:
            try: tracker.transport_closed()
            except (OSError, ValueError, RuntimeError): pass

    def heartbeat():
        while not done.wait(15):
            try: tracker.heartbeat()
            except (OSError, ValueError, RuntimeError):
                # Existing lease/participant stays stale, therefore unknown.
                return

    previous={}
    def forward(signum, frame):
        if child.poll() is None:child.send_signal(signum)
    for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP):
        previous[signum]=signal.signal(signum,forward)
    threads=[threading.Thread(target=f,daemon=True) for f in (client_reader,backend_reader,heartbeat)]
    for thread in threads:thread.start()
    try:
        code=child.wait()
        threads[1].join()
        if tracker.backend_exit(code):participant.remove()
        return code if code>=0 else 128-code
    finally:
        done.set();threads[2].join()
        for signum,handler in previous.items():signal.signal(signum,handler)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend',required=True)
    parser.add_argument('args',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    if not os.path.isabs(args.backend) or not os.access(args.backend,os.X_OK):
        raise ValueError('an absolute executable backend is required')
    argv=args.args[1:] if args.args[:1]==['--'] else args.args
    protocol=work.Protocol()
    if argv[:1]!=['acp']:
        return work.run_job(protocol,[args.backend,*argv])
    return bridge(protocol,[args.backend,*argv])


if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,RuntimeError):
        print('ACP admission unavailable; request not started',file=sys.stderr);sys.exit(75)
