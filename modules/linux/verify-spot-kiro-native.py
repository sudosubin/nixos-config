#!/usr/bin/env python3
"""Explicit real-Kiro canary; root Linux, no network, real credentials or models.

Uses the real native CLI, vendor Bun/TUI and compiled admission proxy/launcher.
Only the native model stream is mocked. Never runs against the host admission
registry or private home. A paused *test* backend makes wire custody observable;
that is not evidence of real model latency or whole-server idle.
"""
import argparse
import ctypes
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pty
import pwd
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import termios
import time
import unittest

spec = importlib.util.spec_from_file_location('work', Path(__file__).with_name('spot_work.py'))
work = importlib.util.module_from_spec(spec)
spec.loader.exec_module(work)
OPTIONS = None
PUBLIC = None
USER = None


class NativeKiroTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix='spot-real-kiro-', dir='/run'))
        self.base.chmod(0o755)
        self.children = []
        self.masters = []
        self.paused = None
        self.addCleanup(self.cleanup)
        self.home = self.base / 'home'
        self.home.mkdir(mode=0o700)
        os.chown(self.home, USER.pw_uid, USER.pw_gid)
        for relative in ['.local/bin', '.local/share/kiro-cli', '.kiro/settings', '.kiro/agents', '.runtime']:
            (self.home / relative).mkdir(parents=True, exist_ok=True)
        for directory in self.home.rglob('*'):
            os.chown(directory, USER.pw_uid, USER.pw_gid)
        for name, source in [('kiro-cli', OPTIONS.frontend), ('kiro-cli-chat', OPTIONS.backend)]:
            (self.home / '.local/bin' / name).symlink_to(source)
        for name in ['bun', 'tui.js']:
            (self.home / '.local/share/kiro-cli' / name).symlink_to(PUBLIC / name)
        agent = self.home / '.kiro/agents/spot-canary.json'
        agent.write_text(json.dumps({'name': 'spot-canary', 'description': 'model-free canary',
                                    'tools': [], 'allowedTools': [], 'mcpServers': {},
                                    'resources': [], 'hooks': {}}))
        agent.chmod(0o644)
        self.mock = self.base / 'mock-model.json'
        self.mock.write_text(json.dumps([['MODEL_FREE_NATIVE_TUI_CANARY'], ['MUST_NOT_REACH_SECOND_MODEL']]))
        self.mock.chmod(0o644)
        runtime = self.base / 'runtime'
        self.protocol = work.Protocol(runtime, uid=USER.pw_uid, gid=USER.pw_gid)
        self.protocol.initialize()
        subprocess.run(['mount', '--bind', str(runtime), '/run/spot-schedule-guard'], check=True)
        self.env = {'HOME': str(self.home), 'USER': USER.pw_name, 'LOGNAME': USER.pw_name,
                    'PATH': str(self.home / '.local/bin') + ':' + str(Path(OPTIONS.frontend).parent)
                            + ':/run/current-system/sw/bin',
                    'XDG_RUNTIME_DIR': str(self.home / '.runtime'), 'TERM': 'xterm-256color',
                    'KIRO_API_KEY': 'test-only-nonfunctional-no-network-key',
                    'KIRO_MOCK_CHAT_RESPONSE': str(self.mock), 'KIRO_DISABLE_TELEMETRY': 'true',
                    'KIRO_NO_AUTO_UPDATE': '1', 'AWS_EC2_METADATA_DISABLED': 'true',
                    'SPOT_ACP_REAL_BACKEND': OPTIONS.backend}

    def cleanup(self):
        if self.paused is not None:
            pid, start = self.paused
            if work.process_start(pid) == start:
                os.kill(pid, signal.SIGCONT)
        for child in self.children:
            try:
                os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=5)
            for stream in [child.stdin, child.stdout, child.stderr]:
                if stream is not None and not stream.closed:
                    stream.close()
        # The real vendor TUI deliberately detaches the ACP process group.
        # Reap only its PID/start-bound test participant, never a host process.
        for record in self.records():
            pid = record['pid']
            if work.process_start(pid) == record['pid_start'] and os.getpgid(pid) == pid:
                try:
                    os.killpg(pid, signal.SIGCONT)
                    os.killpg(pid, signal.SIGTERM)
                    time.sleep(0.1)
                    if work.process_start(pid) == record['pid_start']:
                        os.killpg(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        for master in self.masters:
            os.close(master)
        subprocess.run(['umount', '/run/spot-schedule-guard'], check=True)
        shutil.rmtree(self.base)

    def demote(self, terminal=None):
        def child_setup():
            os.setsid()
            if terminal is not None:
                fcntl.ioctl(terminal, termios.TIOCSCTTY, 0)
            os.initgroups(USER.pw_name, USER.pw_gid)
            os.setgid(USER.pw_gid)
            os.setuid(USER.pw_uid)
            if ctypes.CDLL(None).prctl(38, 1, 0, 0, 0) != 0:
                os._exit(125)
        return child_setup

    def records(self):
        with self.protocol.locked():
            return [json.loads(path.read_text()) for path in (self.protocol.runtime / 'participants').iterdir()]

    def await_condition(self, condition, timeout=35):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if condition():
                return
            time.sleep(0.02)
        self.fail('isolated native Kiro condition not reached; participant metadata='
                  + json.dumps(self.records()) + '; fresh-fixture-only console='
                  + repr(getattr(self, 'last_console', b'')[-5000:]))

    def idle(self):
        records = self.records()
        return (len(records) == 1 and records[0]['healthy'] and records[0]['initialized']
                and records[0]['active_requests'] == 0 and records[0]['server_requests'] == 0)

    def assert_still_unverified(self):
        self.assertEqual([b['reason'] for b in self.protocol.blockers()], ['participant_unverified'])

    def test_compiled_launcher_refuses_bypasses_missing_runtime_and_fenced_start(self):
        for arguments in [['--legacy-ui'], ['--classic'], ['--v3'], ['--agent-engine=v1'],
                          ['--no-interactive'], ['--list-models'], ['--list-sessions'],
                          ['--delete-session=fixture']]:
            with self.subTest(arguments=arguments):
                result = subprocess.run([OPTIONS.launcher, *arguments], env=self.env, cwd=self.home,
                                        preexec_fn=self.demote(), capture_output=True, timeout=8)
                self.assertEqual(result.returncode, 75)
                self.assertIn(b'this route is not tracked', result.stderr)
        bun = self.home / '.local/share/kiro-cli/bun'
        bun.unlink()
        result = subprocess.run([OPTIONS.launcher], env=self.env, cwd=self.home,
                                preexec_fn=self.demote(), capture_output=True, timeout=8)
        self.assertEqual(result.returncode, 75)
        self.assertIn(b'refusing fallback', result.stderr)
        bun.symlink_to(PUBLIC / 'bun')
        self.protocol.seal()
        result = subprocess.run([OPTIONS.launcher], env=self.env, cwd=self.home,
                                preexec_fn=self.demote(), capture_output=True, timeout=8)
        self.assertEqual(result.returncode, 75)
        self.assertEqual(self.records(), [])
        self.assertEqual(self.protocol.blockers(), [])

    def test_actual_native_backend_mock_turn_and_fenced_denial(self):
        child = subprocess.Popen([OPTIONS.proxy, 'acp', '--agent', 'spot-canary'],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                 env=self.env, cwd=self.home, preexec_fn=self.demote(), bufsize=0)
        self.children.append(child)
        buffer = b''

        def rpc(ident, method, params):
            nonlocal buffer
            child.stdin.write((json.dumps({'jsonrpc': '2.0', 'id': ident, 'method': method,
                                          'params': params}) + '\n').encode())
            deadline = time.monotonic() + 35
            while time.monotonic() < deadline:
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    message = json.loads(line)
                    if 'method' not in message and message.get('id') == ident:
                        return message
                if select.select([child.stdout], [], [], 0.05)[0]:
                    data = os.read(child.stdout.fileno(), 65536)
                    self.assertTrue(data, 'actual proxy unexpectedly closed')
                    buffer += data
            self.fail('actual native ACP response missing')

        self.assertEqual(rpc(0, 'initialize', {'protocolVersion': 1, 'clientCapabilities': {}})
                         ['result']['protocolVersion'], 1)
        session = rpc(1, 'session/new', {'cwd': str(self.home), 'mcpServers': []})['result']['sessionId']
        self.await_condition(self.idle)
        params = {'sessionId': session, 'prompt': [{'type': 'text', 'text': 'model-free fixture only'}]}
        self.assertEqual(rpc(2, 'session/prompt', params)['result']['stopReason'], 'end_turn')
        self.await_condition(self.idle)
        self.protocol.seal()
        self.assertEqual(rpc(3, 'session/prompt', params)['error']['code'], -32074)
        self.await_condition(self.idle)
        self.assert_still_unverified()

    def test_actual_outer_launcher_vendor_tui_mock_turn_and_pty_denial(self):
        master, slave = pty.openpty()
        self.masters.append(master)
        fcntl.ioctl(slave, termios.TIOCSWINSZ, __import__('struct').pack('HHHH', 40, 120, 0, 0))
        try:
            child = subprocess.Popen([OPTIONS.launcher, '--agent', 'spot-canary'],
                                     stdin=slave, stdout=slave, stderr=slave, env=self.env, cwd=self.home,
                                     preexec_fn=self.demote(slave))
        finally:
            os.close(slave)
        self.children.append(child)
        console = bytearray()

        def read_console():
            while select.select([master], [], [], 0)[0]:
                try:
                    data = os.read(master, 65536)
                except OSError:
                    break
                if not data:
                    break
                console.extend(data)
                if b'\x1b[6n' in data:
                    os.write(master, b'\x1b[1;1R')
            self.assertLess(len(console), 2 * 1024 * 1024, 'unbounded canary terminal output')
            self.last_console = re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', bytes(console))
            return self.last_console

        def ready():
            read_console()
            self.assertIsNone(child.poll(), 'isolated native TUI exited before readiness')
            return self.idle() and not (termios.tcgetattr(master)[3] & termios.ICANON)

        self.await_condition(ready)
        # Let session/new boot writes settle; do not type into the login/bootstrap UI.
        for _ in range(25):
            read_console()
            time.sleep(0.02)
        self.await_condition(ready)
        record = self.records()[0]
        backend = record['backend_pid']
        self.assertEqual(Path('/proc', str(backend), 'exe').resolve(), Path(OPTIONS.backend))
        ancestor = backend
        for _ in range(32):
            if ancestor == child.pid:
                break
            ancestor = int(Path('/proc', str(ancestor), 'stat').read_text().rsplit(')', 1)[1].split()[1])
        self.assertEqual(ancestor, child.pid, 'backend is not a descendant of this isolated native TUI')
        self.assertEqual(os.getpgid(backend), record['pid'])
        self.assertEqual(work.process_start(backend), record['backend_start'])
        self.assertEqual(work.process_uid(backend), USER.pw_uid)
        rejections = record['admission_rejections']
        self.paused = (backend, record['backend_start'])
        os.kill(backend, signal.SIGSTOP)
        try:
            os.write(master, b'Return the fixed model-free canary marker.\r')
            self.await_condition(lambda: (read_console() is not None
                                         and any(r['active_requests'] > 0 for r in self.records())))
            self.assertTrue([b for b in self.protocol.blockers() if b['reason'] != 'participant_unverified'])
            self.protocol.seal()
            # Real PTY input arrives behind the fence while the previously
            # admitted request is still outstanding. Do not cancel that work.
            os.write(master, b'This second fixture must not reach the model.\r')
            self.await_condition(lambda: (read_console() is not None
                                         and any(r['active_requests'] > 0
                                                 and r['admission_rejections'] == rejections + 1
                                                 for r in self.records())))
        finally:
            os.kill(backend, signal.SIGCONT)
            self.paused = None
        self.await_condition(lambda: b'MODEL_FREE_NATIVE_TUI_CANARY' in read_console() and self.idle())
        self.assert_still_unverified()
        # Busy steering masks the server error in this vendor frontend. Check
        # both its actual rejection UI and the proxy's pre-forward counter.
        self.await_condition(lambda: b'Failed to queue message' in read_console())
        os.write(master, b'The idle fixture must also be rejected.\r')
        self.await_condition(lambda: b'Shutdown admission closed; request not started' in read_console())
        self.await_condition(lambda: self.idle() and self.records()[0]['admission_rejections'] == rejections + 2)
        self.assertNotIn(b'MUST_NOT_REACH_SECOND_MODEL', read_console())
        self.assert_still_unverified()


def main():
    global OPTIONS, PUBLIC, USER
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['frontend', 'backend', 'bun', 'tui', 'proxy', 'launcher']:
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--inside-private-namespaces', action='store_true', help=argparse.SUPPRESS)
    OPTIONS = parser.parse_args()
    if sys.platform != 'linux' or os.geteuid() != 0:
        parser.error('explicit verification requires root Linux; skipping is not proof')
    for name in ['frontend', 'backend', 'bun', 'tui', 'proxy', 'launcher']:
        setattr(OPTIONS, name, str(Path(getattr(OPTIONS, name)).resolve(strict=True)))
    if not OPTIONS.inside_private_namespaces:
        return subprocess.call(['unshare', '--mount', '--net', '--pid', '--fork', '--mount-proc',
                                '--kill-child', sys.executable, str(Path(__file__).resolve()),
                                *sys.argv[1:], '--inside-private-namespaces'])
    if os.getpid() != 1:
        parser.error('refusing verification outside a fresh private PID namespace')
    subprocess.run(['mount', '--make-rprivate', '/'], check=True)
    USER = pwd.getpwuid(1001)
    with tempfile.TemporaryDirectory(prefix='spot-native-public-runtime-', dir='/run') as directory:
        PUBLIC = Path(directory)
        PUBLIC.chmod(0o755)
        hashes = {}
        for name, source in [('bun', OPTIONS.bun), ('tui.js', OPTIONS.tui)]:
            target = PUBLIC / name
            shutil.copyfile(source, target)
            target.chmod(0o555 if name == 'bun' else 0o444)
            hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
        # Hide all real personal/recovery files and host user sockets from the
        # real app. Public vendor runtime is copied, not private configuration.
        for index, target in enumerate(['/home', '/root', '/tmp', '/run/user']):
            empty = PUBLIC / ('empty-' + str(index))
            empty.mkdir()
            if target == '/tmp':
                empty.chmod(0o1777)
            subprocess.run(['mount', '--bind', str(empty), target], check=True)
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(NativeKiroTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        print(json.dumps({'native_integration_cases': result.testsRun, 'skipped': len(result.skipped),
                          'failures': len(result.failures), 'errors': len(result.errors),
                          'public_vendor_sha256': hashes, 'network_pid_mount_isolated': True,
                          'real_credentials_models_channels': False,
                          'whole_work_tracking_verified': False, 'production_rollout': False}), flush=True)
        return 0 if result.wasSuccessful() and result.testsRun == 3 and not result.skipped else 1


if __name__ == '__main__':
    sys.exit(main())
