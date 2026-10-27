"""Offline tests. Never invoke AWS or change the running machine."""
import copy
import os
import tempfile
from datetime import datetime
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("guard", Path(__file__).with_name("spot-schedule-guard.py"))
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def at(text):
    return datetime.fromisoformat(text + "+09:00")


class DrainSandboxMixin:
    def setUp(self):
        super().setUp()
        self.drain_temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.drain_temp.cleanup)
        counter = [0]
        def transaction(config, protocol):
            for key,value in {'account':'537112465379','region':'ap-northeast-2','asg':'test-asg',
                              'home_volume':'vol-test','home_uuid':'test-uuid'}.items():
                config.setdefault(key,value)
            from unittest.mock import Mock
            if isinstance(protocol, Mock):
                protocol.state.return_value = 'open'
                protocol.seal.side_effect = lambda attempt: setattr(protocol.state, 'return_value', 'draining')
            counter[0] += 1
            return guard.spot_drain.Transaction(config, protocol,
                Path(self.drain_temp.name)/str(counter[0])/'drain.json', owner_uid=os.geteuid(),
                current_owner={'boot_id':'test','pid':os.getpid(),'pid_start':1,'pid_namespace':'unit-test'})
        for name,kwargs in [('drain_transaction',{'side_effect':transaction}),
                            ('capture_services',{'side_effect':lambda cfg:{'user@%d.service'%cfg['uid']:'active','docker.service':'active'}}),
                            ('verify_recovery_home',{}),('verify_recovery_services',{}),('backup_cold_check',{})]:
            patcher=patch.object(guard,name,**kwargs);patcher.start();self.addCleanup(patcher.stop)
        patcher=patch.object(guard.spot_cold,'configured');patcher.start();self.addCleanup(patcher.stop)


class ScheduleTests(unittest.TestCase):
    def test_weekday_boundaries(self):
        for clock, expected in [("01:59:59", True), ("02:00:00", False), ("16:29:59", False), ("16:30:00", True), ("23:59:59", True)]:
            with self.subTest(clock=clock):
                self.assertEqual(guard.running_window(at("2026-10-26T" + clock)), expected)

    def test_weekend_boundaries(self):
        for date in ["2026-10-24", "2026-10-25"]:
            for clock, expected in [("01:59:59", True), ("02:00:00", False), ("10:29:59", False), ("10:30:00", True)]:
                with self.subTest(date=date, clock=clock):
                    self.assertEqual(guard.running_window(at(date + "T" + clock)), expected)

    def test_utc_is_converted(self):
        self.assertTrue(guard.running_window(datetime.fromisoformat("2026-10-26T07:30:00+00:00")))
        self.assertFalse(guard.running_window(datetime.fromisoformat("2026-10-26T07:29:59+00:00")))

    def test_naive_time_is_rejected(self):
        with self.assertRaises(ValueError):
            guard.running_window(datetime(2026, 10, 26, 2))


class SafetyTests(DrainSandboxMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.config = {"armed": True, "home_uuid": "uuid", "instance_id": "i-test"}
        self.group = {"DesiredCapacity": 0}
        self.now = at("2026-10-26T02:15:00")
        self.node = {
            "mounted": True, "uuid": "uuid", "system": "/nix/store/system", "profile": "/nix/store/profile",
            "manifest": {**{key: True for key in guard.REQUIRED}, "system": "/nix/store/system", "user_profile": "/nix/store/profile"},
            "workers": [], "leases": [], "maintenance": False,
        }
        self.volume = {"Encrypted": True, "Attachments": [{"InstanceId": "i-test", "State": "attached", "DeleteOnTermination": False}]}

    def reasons(self, sessions=None):
        return guard.reasons(self.config, self.now, self.group, self.node, sessions or [], self.volume)

    def test_verified_idle_can_be_considered(self):
        self.assertEqual(self.reasons(), [])

    def test_observation_never_releases(self):
        self.config["armed"] = False
        self.assertIn("observation_mode", self.reasons())

    def test_missing_arming_is_observation(self):
        del self.config["armed"]
        self.assertIn("observation_mode", self.reasons())

    def test_each_prerequisite_is_mandatory(self):
        for key in guard.REQUIRED:
            with self.subTest(key=key):
                manifest = self.node["manifest"]
                saved = manifest.pop(key)
                self.assertIn("prerequisite:" + key, self.reasons())
                manifest[key] = saved

    def test_truthy_strings_cannot_arm_prerequisites(self):
        self.node["manifest"]["replacement_verified"] = "true"
        self.assertIn("prerequisite:replacement_verified", self.reasons())

    def test_ssm_session_blocks(self):
        self.assertIn("active_ssm_sessions", self.reasons([{"SessionId": "human"}]))

    def test_unmounted_home_blocks(self):
        self.node["mounted"] = False
        self.assertIn("home_not_verified", self.reasons())

    def test_wrong_uuid_blocks(self):
        self.node["uuid"] = "wrong"
        self.assertIn("home_not_verified", self.reasons())

    def test_profile_and_system_drift_block(self):
        for field in ["system", "profile"]:
            with self.subTest(field=field):
                node = copy.deepcopy(self.node)
                node[field] = "changed"
                self.assertIn("profile_drift", guard.reasons(self.config, self.now, self.group, node, [], self.volume))

    def test_missing_profile_cache_blocks(self):
        self.config["profile_cache_manifest"] = "cache.json"
        self.assertIn("profile_cache_not_current", self.reasons())

    def test_new_profile_allowed_only_after_atomic_cache_publication(self):
        self.config["profile_cache_manifest"] = "cache.json"
        self.node["profile"] = "/nix/store/new-profile"
        self.assertIn("profile_cache_not_current", self.reasons())
        self.node["profile_cache"] = {"schema":1,"system":self.node["system"],"user_profile":self.node["profile"],"roots":[self.node["system"],self.node["profile"]]}
        self.assertEqual(self.reasons(), [])

    def test_cache_cannot_approve_an_unverified_system(self):
        self.config["profile_cache_manifest"] = "cache.json"
        self.node["system"] = "/nix/store/new-system"
        self.node["profile_cache"] = {"schema":1,"system":self.node["system"],"user_profile":self.node["profile"],"roots":[self.node["system"],self.node["profile"]]}
        self.assertIn("profile_drift", self.reasons())

    def test_invalid_profile_cache_schema_and_roots_block(self):
        self.config["profile_cache_manifest"] = "cache.json"
        for change in [{"schema":True},{"schema":"1"},{"roots":[]},{"roots":None},{"system":"other"},{"user_profile":"other"}]:
            with self.subTest(change=change):
                self.node["profile_cache"] = {"schema":1,"system":self.node["system"],"user_profile":self.node["profile"],"roots":[self.node["system"],self.node["profile"]],**change}
                self.assertIn("profile_cache_not_current", self.reasons())

    def test_jobs_and_maintenance_block(self):
        for field, value, expected in [("workers", [{"name":"kiro-cli-chat"}], "untracked_workers"), ("leases", ["invalid_lease"], "active_or_invalid_leases"), ("maintenance", True, "maintenance_running")]:
            with self.subTest(field=field):
                node = copy.deepcopy(self.node)
                node[field] = value
                self.assertIn(expected, guard.reasons(self.config, self.now, self.group, node, [], self.volume))

    def test_unencrypted_home_blocks(self):
        self.volume["Encrypted"] = False
        self.assertIn("home_encryption_not_ready", self.reasons())

    def test_foreign_or_detaching_volume_blocks(self):
        for attachment in [{"InstanceId":"i-other","State":"attached"}, {"InstanceId":"i-test","State":"detaching"}]:
            with self.subTest(attachment=attachment):
                self.volume["Attachments"] = [attachment]
                self.assertIn("home_attachment_not_verified", self.reasons())

    def test_deletable_or_unknown_home_attachment_blocks(self):
        for value in [True, None, "false"]:
            with self.subTest(value=value):
                self.volume["Attachments"][0]["DeleteOnTermination"] = value
                self.assertIn("home_attachment_not_verified", self.reasons())

    def test_next_morning_start_cancels_previous_stop(self):
        self.now = at("2026-10-26T16:30:00")
        self.assertIn("scheduled_running_window", self.reasons())

    def test_nonzero_desired_blocks_even_outside_window(self):
        self.group["DesiredCapacity"] = 1
        self.assertIn("asg_not_requesting_scale_in", self.reasons())

    def test_busy_rechecks_on_15_minute_boundary(self):
        self.now = at("2026-10-26T02:16:00")
        self.assertIn("waiting_15_minute_recheck", self.reasons())

    def test_drain_cancels_before_stopping_services_if_schedule_resumes(self):
        self.config["uid"] = 1001
        with patch.object(guard, "work_protocol"), patch.object(guard, "group_state", return_value={"Instances":[{"InstanceId":"i-test","ProtectedFromScaleIn":True}]}), patch.object(guard, "running_window", return_value=True), patch.object(guard, "protection") as protection, patch.object(guard, "command") as command, patch.object(guard, "RUNTIME") as runtime, patch.object(guard.subprocess, "run"):
            with self.assertRaises(RuntimeError):
                guard.drain(self.config)
            command.assert_not_called()
            protection.assert_called_once_with(self.config, True)


def completed_backup():
    # These tests cover the guard transition, not the snapshot API. The actual
    # lifecycle/ownership/retention contracts are tested in test-spot-backup.py.
    from unittest.mock import MagicMock
    result=MagicMock()
    result.capture.return_value={'Encrypted':True,'State':'completed','SnapshotId':'snap-test'}
    return result


class GatewayDrainTests(DrainSandboxMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.backup=completed_backup()
        patcher=patch.object(guard.spot_backup,'configured',return_value=self.backup)
        patcher.start();self.addCleanup(patcher.stop)

    def test_busy_gateway_rolls_back_before_other_services_stop(self):
        from unittest.mock import MagicMock
        cfg={'uid':1001,'instance_id':'i-test','gateway':{'unit':'test-gateway.service'}};gateway=MagicMock();gateway.manager.unit='test-gateway.service';gateway.acquire.side_effect=RuntimeError('busy')
        with patch.object(guard,'work_protocol') as protocol, patch.object(guard.spot_gateway,'configured',return_value=gateway), patch.object(guard,'shutdown_request_current'), patch.object(guard,'protection'), patch.object(guard,'group_state',return_value={'Instances':[{'InstanceId':'i-test','ProtectedFromScaleIn':True}]}), patch.object(guard,'command') as command:
            with self.assertRaises(RuntimeError):guard.drain(cfg)
            command.assert_not_called();gateway.rollback.assert_called_once();protocol.return_value.unseal.assert_called_once()

    def test_gateway_recovery_failure_cannot_reopen_admission(self):
        from unittest.mock import MagicMock
        cfg={'uid':1001,'instance_id':'i-test','gateway':{'unit':'test-gateway.service'}};gateway=MagicMock();gateway.manager.unit='test-gateway.service';gateway.acquire.side_effect=RuntimeError('busy');gateway.rollback.side_effect=RuntimeError('recovery unknown')
        with patch.object(guard,'work_protocol') as protocol, patch.object(guard.spot_gateway,'configured',return_value=gateway), patch.object(guard,'shutdown_request_current'), patch.object(guard,'protection'), patch.object(guard,'group_state',return_value={'Instances':[{'InstanceId':'i-test','ProtectedFromScaleIn':True}]}):
            with self.assertRaises(RuntimeError):guard.drain(cfg)
            protocol.return_value.unseal.assert_not_called()

    def test_gateway_stop_precedes_user_manager_and_home_stop(self):
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        events=[];gateway=MagicMock();gateway.acquire.side_effect=lambda:events.append('acquire');gateway.stop.side_effect=lambda:events.append('gateway_stop')
        cfg={'uid':1001,'home_volume':'vol','instance_id':'i-test'}
        def command(*args,**kwargs):events.append(args[2] if len(args)>2 else 'command')
        with patch.object(guard,'work_protocol'), patch.object(guard.spot_gateway,'configured',return_value=gateway), patch.object(guard,'shutdown_request_current'), patch.object(guard,'drain_recheck'), patch.object(guard,'command',side_effect=command), patch.object(guard.subprocess,'run',return_value=SimpleNamespace(returncode=1)), patch.object(guard,'aws',return_value={'Encrypted':True,'SnapshotId':'snap'}), patch.object(guard,'protection'), patch.object(guard,'status'):
            guard.drain(cfg)
        self.assertLess(events.index('acquire'),events.index('gateway_stop'));self.assertLess(events.index('gateway_stop'),events.index('user@1001.service'));self.assertLess(events.index('user@1001.service'),events.index('home.mount'))

    def test_stopped_gateway_exemption_requires_confirmed_unit_state(self):
        from unittest.mock import MagicMock
        gateway=MagicMock();gateway.stopped=True;gateway.manager.assert_stopped=MagicMock(side_effect=RuntimeError('not stopped'))
        with patch.object(guard,'group_state'),patch.object(guard,'probe') as probe:
            with self.assertRaises(RuntimeError):guard.drain_recheck({},gateway)
            probe.assert_not_called()

    def test_readonly_gateway_projection_is_mandatory_when_configured(self):
        test=SafetyTests();test.setUp();self.addCleanup(test.doCleanups);test.config['gateway']={'enabled':True}
        self.assertIn('gateway_status_unknown',test.reasons())
        test.node['gateway']={'observable':True,'maintenance_busy':True}
        self.assertIn('gateway_maintenance_busy',test.reasons())


class StartupTests(unittest.TestCase):
    def test_startup_requires_confirmed_protection(self):
        cfg = {"instance_id":"i-test"}
        group = {"Instances":[{"InstanceId":"i-test","ProtectedFromScaleIn":True}]}
        with patch.object(guard,"group_state",return_value=group), patch.object(guard,"protection") as protect, patch.object(guard,"status"), patch.object(guard.clock,"sleep") as sleep:
            guard.startup_protection(cfg)
            protect.assert_called_once_with(cfg,True)
            sleep.assert_not_called()

    def test_pending_membership_retries_without_releasing(self):
        cfg = {"instance_id":"i-test"}
        group = {"Instances":[{"InstanceId":"i-test","ProtectedFromScaleIn":True}]}
        with patch.object(guard,"group_state",side_effect=[ValueError("Pending"),group,group]), patch.object(guard,"protection") as protect, patch.object(guard,"status"), patch.object(guard.clock,"sleep") as sleep:
            guard.startup_protection(cfg)
            protect.assert_called_once_with(cfg,True)
            sleep.assert_called_once_with(5)

    def test_unconfirmed_protection_cannot_open_startup_gate(self):
        group = {"Instances":[{"InstanceId":"i-test","ProtectedFromScaleIn":False}]}
        with patch.object(guard,"group_state",return_value=group), patch.object(guard,"protection") as protect, patch.object(guard,"status") as status, self.assertRaises(RuntimeError):
            guard.startup_protection({"instance_id":"i-test"},timeout=0)
        protect.assert_called_once()
        status.assert_not_called()


class FailureTests(DrainSandboxMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.backup=completed_backup()
        patcher=patch.object(guard.spot_backup,'configured',return_value=self.backup)
        patcher.start();self.addCleanup(patcher.stop)

    def test_api_failure_after_protection_never_releases(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            cfg = {"account": "account", "region": "region"}
            with patch("sys.argv", ["guard"]), patch.object(guard, "RUNTIME", Path(tmp)), patch.object(guard, "root_json", return_value=cfg), patch.object(guard, "identity", return_value={"accountId":"account","region":"region","instanceId":"i-test"}), patch.object(guard, "group_state", return_value={"DesiredCapacity":0}), patch.object(guard, "protection") as protection, patch.object(guard, "probe", side_effect=RuntimeError("API unavailable")), patch.object(guard, "status"):
                with self.assertRaises(RuntimeError):
                    guard.main()
                protection.assert_called_once_with(cfg, True)

    def test_wrong_identity_cannot_release_protection(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            with patch("sys.argv", ["guard"]), patch.object(guard, "RUNTIME", Path(tmp)), patch.object(guard, "root_json", return_value={"account":"expected","region":"region"}), patch.object(guard, "identity", return_value={"accountId":"wrong","region":"region"}), patch.object(guard, "protection") as protection, patch.object(guard, "status"):
                with self.assertRaises(ValueError):
                    guard.main()
                protection.assert_not_called()

    def test_snapshot_failure_restores_services_and_keeps_protection(self):
        from types import SimpleNamespace
        cfg = {"uid":1001,"home_volume":"vol-test","instance_id":"i-test"}
        self.backup.capture.side_effect=RuntimeError('snapshot failed')
        with patch.object(guard, "work_protocol"), patch.object(guard, "drain_recheck"), patch.object(guard, "RUNTIME"), patch.object(guard, "running_window", return_value=False), patch.object(guard, "group_state", return_value={"DesiredCapacity":0,"Instances":[{"InstanceId":"i-test","ProtectedFromScaleIn":True}]}), patch.object(guard, "sessions", return_value=[]), patch.object(guard, "command"), patch.object(guard.subprocess, "run", return_value=SimpleNamespace(returncode=1)) as run, patch.object(guard, "aws", side_effect=RuntimeError("snapshot failed")), patch.object(guard, "protection") as protection:
            with self.assertRaises(RuntimeError):
                guard.drain(cfg)
            protection.assert_called_once_with(cfg, True)
            self.assertTrue(any(c.args[0][:3] == ["systemctl","start","home.mount"] for c in run.call_args_list))

    def test_truthy_non_boolean_arming_does_not_arm(self):
        case = SafetyTests()
        case.setUp();self.addCleanup(case.doCleanups)
        for value in ["true", "false", 1, None]:
            with self.subTest(value=value):
                case.config["armed"] = value
                self.assertIn("observation_mode", case.reasons())


class AdmissionDrainTests(DrainSandboxMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        import os,tempfile
        from contextlib import ExitStack
        from types import SimpleNamespace
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.protocol=guard.work.Protocol(Path(self.temp.name)/'runtime',uid=os.geteuid(),gid=os.getegid(),root_uid=os.geteuid(),boot_id='test')
        self.protocol.initialize()
        self.cfg={'uid':1001,'instance_id':'i-test','home_volume':'vol-test'}
        self.group={'DesiredCapacity':0,'Instances':[{'InstanceId':'i-test','ProtectedFromScaleIn':True}]}
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        def mock(name,**kwargs):return self.stack.enter_context(patch.object(guard,name,**kwargs))
        mock('work_protocol',return_value=self.protocol);mock('running_window',return_value=False)
        self.group_mock=mock('group_state',return_value=self.group);mock('sessions',return_value=[])
        self.recheck=mock('drain_recheck');self.command=mock('command')
        self.run=self.stack.enter_context(patch.object(guard.subprocess,'run',return_value=SimpleNamespace(returncode=1)))
        self.backup=completed_backup()
        self.stack.enter_context(patch.object(guard.spot_backup,'configured',return_value=self.backup))
        self.aws=self.backup.capture
        self.protection=mock('protection');self.status=mock('status')

    def test_extension_after_snapshot_cancels_before_release(self):
        def snapshot(*args):
            self.protocol.create('manual',100)
            return {'Encrypted':True,'State':'completed','SnapshotId':'snap-test'}
        self.aws.side_effect=snapshot
        with self.assertRaises(RuntimeError):guard.drain(self.cfg)
        self.protection.assert_called_once_with(self.cfg,True)
        self.assertEqual(self.protocol.state(),'open')
        self.assertTrue(self.protocol.blockers())

    def test_post_fence_preflight_failure_never_stops_services(self):
        self.recheck.side_effect=RuntimeError('new work')
        with self.assertRaises(RuntimeError):guard.drain(self.cfg)
        self.command.assert_not_called();self.run.assert_not_called()
        self.assertEqual(self.protocol.state(),'open')

    def test_post_stop_recheck_failure_restores_services(self):
        self.recheck.side_effect=[None,RuntimeError('new session')]
        with self.assertRaises(RuntimeError):guard.drain(self.cfg)
        self.aws.assert_not_called();self.assertEqual(self.run.call_count,2)
        self.assertEqual(self.protocol.state(),'open')

    def test_acknowledged_extension_cancels_long_backup_poll(self):
        self.protocol.seal();self.protocol.create('manual',100)
        with patch.object(guard,'shutdown_request_current'),patch.object(guard,'command') as command:
            with self.assertRaises(RuntimeError):guard.backup_wait_checkpoint(self.cfg,self.protocol,None)
            command.assert_not_called()
        self.assertTrue(self.protocol.blockers())

    def test_pending_create_reply_cannot_release_protection(self):
        self.backup.capture.return_value={'Encrypted':True,'State':'pending','SnapshotId':'snap-test'}
        with self.assertRaises(RuntimeError):guard.drain(self.cfg)
        self.protection.assert_called_once_with(self.cfg,True)
        self.assertEqual(self.protocol.state(),'open')

    def test_completed_backup_is_revalidated_inside_final_release_lock(self):
        self.backup.successful.side_effect=RuntimeError('snapshot disappeared')
        with self.assertRaises(RuntimeError):guard.drain(self.cfg)
        self.protection.assert_called_once_with(self.cfg,True)
        self.assertEqual(self.protocol.state(),'open')

    def test_success_keeps_admission_closed_and_releases_only_last(self):
        guard.drain(self.cfg)
        self.protection.assert_called_once_with(self.cfg,False)
        self.assertEqual(self.protocol.state(),'released')
        with self.assertRaises(RuntimeError):self.protocol.create('manual',100)

    def test_release_timeout_reprotects_before_reopening(self):
        self.protection.side_effect=[RuntimeError('AWS timeout'),None]
        with self.assertRaises(RuntimeError):guard.drain(self.cfg)
        self.assertEqual([c.args[1] for c in self.protection.call_args_list],[False,True])
        self.assertEqual(self.protocol.state(),'open')

    def test_unconfirmed_reprotection_never_reopens_or_restarts(self):
        self.protection.side_effect=[RuntimeError('AWS timeout'),None]
        self.group_mock.return_value={'DesiredCapacity':0,'Instances':[{'InstanceId':'i-test','ProtectedFromScaleIn':False}]}
        with self.assertRaises(RuntimeError):guard.drain(self.cfg)
        self.assertEqual(self.protocol.state(),'releasing')
        self.assertEqual(self.run.call_count,1)  # findmnt, not service restarts

    def test_failed_rollback_mount_keeps_admission_closed(self):
        import subprocess
        from types import SimpleNamespace
        self.aws.side_effect=RuntimeError('snapshot failed')
        self.run.side_effect=[SimpleNamespace(returncode=1),subprocess.CalledProcessError(1,['mount'])]
        with self.assertRaises(subprocess.CalledProcessError):guard.drain(self.cfg)
        self.assertEqual(self.protocol.state(),'draining')

    def test_kernel_claim_is_held_through_backup_and_release(self):
        held=[False]
        class Claim:
            def __enter__(self):held[0]=True;return self
            def __exit__(self,*args):held[0]=False
        def capture():
            self.assertTrue(held[0]);return {'Encrypted':True,'State':'completed','SnapshotId':'snap-test'}
        self.backup.capture.side_effect=capture
        self.protection.side_effect=lambda cfg,value:self.assertTrue(held[0]) if value is False else None
        with patch.object(guard.spot_cold,'configured',return_value=Claim()):guard.drain(self.cfg)
        self.assertFalse(held[0]);self.assertEqual(self.protocol.state(),'released')

    def test_failed_backup_releases_kernel_claim_before_mount_rollback(self):
        from types import SimpleNamespace
        held=[False]
        class Claim:
            def __enter__(self):held[0]=True;return self
            def __exit__(self,*args):held[0]=False
        self.backup.capture.side_effect=RuntimeError('test-only snapshot failure')
        def run(args,**kwargs):
            if args[:3]==['systemctl','start','home.mount']:self.assertFalse(held[0])
            return SimpleNamespace(returncode=1)
        self.run.side_effect=run
        with patch.object(guard.spot_cold,'configured',return_value=Claim()),self.assertRaises(RuntimeError):guard.drain(self.cfg)
        self.assertFalse(held[0]);self.assertEqual(self.protocol.state(),'open')

    def test_status_failure_after_release_cannot_admit_new_work(self):
        self.status.side_effect=OSError('log full')
        with self.assertRaises(OSError):guard.drain(self.cfg)
        self.protection.assert_called_once_with(self.cfg,False)
        self.assertEqual(self.protocol.state(),'released')
        self.assertEqual(self.run.call_count,1)


class ColdBackupChecks(unittest.TestCase):
    def setUp(self):
        from unittest.mock import Mock
        self.claim=Mock()

    def test_missing_real_kernel_claim_cannot_be_a_cold_success(self):
        with patch.object(guard,'aws') as aws,patch.object(guard.subprocess,'run') as run,self.assertRaises(RuntimeError):
            guard.backup_cold_check({'home_uuid':'uuid'})
        aws.assert_not_called();run.assert_not_called()

    def test_lost_kernel_claim_cannot_be_a_cold_success(self):
        self.claim.check.side_effect=RuntimeError('claim lost')
        with patch.object(guard,'aws') as aws,patch.object(guard.subprocess,'run') as run,self.assertRaises(RuntimeError):
            guard.backup_cold_check({'home_uuid':'uuid'},self.claim)
        aws.assert_not_called();run.assert_not_called()

    def test_any_mount_of_home_UUID_blocks_cold_claim(self):
        from types import SimpleNamespace
        with patch.object(guard.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=b'/elsewhere')),patch.object(guard,'aws') as aws:
            with self.assertRaises(RuntimeError):guard.backup_cold_check({'home_uuid':'uuid'},self.claim)
            aws.assert_not_called()

    def test_unknown_mount_query_not_unmounted(self):
        from types import SimpleNamespace
        with patch.object(guard.subprocess,'run',return_value=SimpleNamespace(returncode=2,stdout=b'')):
            with self.assertRaises(RuntimeError):guard.backup_cold_check({'home_uuid':'uuid'},self.claim)

    def test_cold_source_must_still_be_exact_protected_attachment(self):
        from types import SimpleNamespace
        cfg={'home_uuid':'uuid','home_volume':'vol-test','instance_id':'i-test'}
        for change in [{'InstanceId':'other','State':'attached','DeleteOnTermination':False},{'InstanceId':'i-test','State':'attached','DeleteOnTermination':True}]:
            with self.subTest(change=change),patch.object(guard.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout=b'')),patch.object(guard,'aws',return_value={'Volumes':[{'VolumeId':'vol-test','Encrypted':True,'Attachments':[change]}]}):
                with self.assertRaises(RuntimeError):guard.backup_cold_check(cfg,self.claim)

    def test_shutdown_superseded_cancels_backup_polling(self):
        from unittest.mock import MagicMock
        with patch.object(guard,'shutdown_request_current',side_effect=RuntimeError('new native start')),patch.object(guard,'command') as command:
            with self.assertRaises(RuntimeError):guard.backup_wait_checkpoint({},MagicMock(),None)
            command.assert_not_called()

    def test_new_service_activity_during_backup_is_unknown_not_idle(self):
        from unittest.mock import MagicMock
        protocol=MagicMock();protocol.state.return_value='draining';protocol.blockers_unlocked.return_value=[]
        with patch.object(guard,'shutdown_request_current'),patch.object(guard,'command',return_value='active inactive'):
            with self.assertRaises(RuntimeError):guard.backup_wait_checkpoint({'uid':1001},protocol,None)

    def test_non_idempotent_create_disables_sdk_retry_and_scrubs_operator_credentials(self):
        from types import SimpleNamespace
        import os
        with patch.dict(os.environ,{'AWS_PROFILE':'operator','AWS_ACCESS_KEY_ID':'not-forwarded'}),patch.object(guard.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='',stderr='An error occurred (UnauthorizedOperation) PRIVATE_DIAGNOSTIC')) as run:
            with self.assertRaises(guard.spot_backup.AWSFailure) as error:guard.aws({'region':'ap-northeast-2'},'ec2','create-snapshot')
            env=run.call_args.kwargs['env'];self.assertEqual(env['AWS_MAX_ATTEMPTS'],'1');self.assertNotIn('AWS_ACCESS_KEY_ID',env);self.assertNotIn('AWS_PROFILE',env)
            self.assertNotIn('PRIVATE_DIAGNOSTIC',str(error.exception))


class RecoveryRoutingTests(unittest.TestCase):
    def test_recover_only_without_journal_never_starts_a_new_shutdown(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg={'account':'account','region':'region','drain_journal':str(Path(directory)/'missing.json')}
            with patch('sys.argv',['guard','--recover-only']),patch.object(guard,'RUNTIME',Path(directory)),patch.object(guard,'root_json',return_value=cfg),patch.object(guard,'identity',return_value={'accountId':'account','region':'region','instanceId':'i-test'}),patch.object(guard,'startup_protection') as protect,patch.object(guard,'probe') as probe,patch.object(guard,'drain') as drain,patch.object(guard,'status'):
                guard.main();protect.assert_called_once_with(cfg);probe.assert_not_called();drain.assert_not_called()

    def test_pending_drain_is_reconciled_before_any_mounted_home_probe(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'drain.json';path.write_text('{}')
            cfg={'account':'account','region':'region','uid':1001,'drain_journal':str(path)}
            transaction=MagicMock();transaction.read.return_value={'phase':'home_unmounted'}
            with patch('sys.argv',['guard']),patch.object(guard,'RUNTIME',Path(directory)),patch.object(guard,'root_json',return_value=cfg),patch.object(guard,'identity',return_value={'accountId':'account','region':'region','instanceId':'i-test'}),patch.object(guard,'drain_transaction',return_value=transaction),patch.object(guard,'reconcile_drain',return_value='recovered') as recover,patch.object(guard,'probe') as probe,patch.object(guard,'drain') as drain,patch.object(guard,'status'):
                guard.main();recover.assert_called_once();probe.assert_not_called();drain.assert_not_called()


class RecoveryIOTests(unittest.TestCase):
    def setUp(self):
        from contextlib import ExitStack
        from types import SimpleNamespace
        from unittest.mock import MagicMock
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.cfg={'uid':1001,'instance_id':'i-test','home_volume':'vol-0123456789abcdef0','home_uuid':'test-uuid'}
        self.volume={'VolumeId':self.cfg['home_volume'],'Attachments':[{'InstanceId':'i-test','State':'attached','DeleteOnTermination':False}]}
        self.serial=MagicMock();self.serial.read_text.return_value=self.cfg['home_volume'].replace('-','');self.serial.parent.parent.name='nvme127n1'
        self.serials=[self.serial];self.alias=Path('/dev/nvme127n1');self.targets='/home';self.mount_code=0
        self.mounted='test-uuid rw,relatime / /dev/nvme127n1';self.started=[]
        def path(value,*args):
            real=Path(value,*args)
            if str(real)=='/sys/class/block':return SimpleNamespace(glob=lambda pattern:self.serials)
            if str(real)=='/dev/disk/by-uuid/test-uuid':return SimpleNamespace(resolve=lambda:self.alias)
            return real
        def command(*args,**kwargs):
            if args[0]=='blkid':return 'test-uuid'
            if args[0]=='findmnt':return self.mounted
            if args[:2]==('systemctl','show'):return 'active'
            raise AssertionError(args)
        def run(args,**kwargs):
            if args[0]=='findmnt':return SimpleNamespace(returncode=self.mount_code,stdout=self.targets)
            if args[:3]==['systemctl','start','home.mount']:
                self.started.append(args);self.mount_code=0;self.targets='/home'
                return SimpleNamespace(returncode=0)
            raise AssertionError(args)
        self.stack.enter_context(patch.object(guard,'Path',side_effect=path))
        self.api=self.stack.enter_context(patch.object(guard,'aws',return_value={'Volumes':[self.volume]}))
        self.stack.enter_context(patch.object(guard,'command',side_effect=command))
        self.stack.enter_context(patch.object(guard.subprocess,'run',side_effect=run))

    def test_exact_current_writable_home_is_observed_without_restart(self):
        guard.verify_recovery_home(self.cfg,allow_mount=True);self.assertEqual(self.started,[])

    def test_unmounted_home_is_started_only_after_exact_device_validation(self):
        self.mount_code=1;self.targets=''
        guard.verify_recovery_home(self.cfg,allow_mount=True)
        self.assertEqual(self.started,[['systemctl','start','home.mount']])

    def test_wrong_attachment_delete_flag_or_volume_never_mounts(self):
        for field,value in [('InstanceId','other'),('State','detaching'),('DeleteOnTermination',True)]:
            saved=self.volume['Attachments'][0][field];self.volume['Attachments'][0][field]=value
            with self.subTest(field=field),self.assertRaises(RuntimeError):guard.verify_recovery_home(self.cfg,allow_mount=True)
            self.volume['Attachments'][0][field]=saved
        self.assertEqual(self.started,[])

    def test_missing_duplicate_serial_or_wrong_uuid_alias_never_mounts(self):
        for devices in [[],[self.serial,self.serial]]:
            self.serials=devices
            with self.assertRaises(RuntimeError):guard.verify_recovery_home(self.cfg,allow_mount=True)
        self.serials=[self.serial];self.alias=Path('/dev/other')
        with self.assertRaises(RuntimeError):guard.verify_recovery_home(self.cfg,allow_mount=True)
        self.assertEqual(self.started,[])

    def test_other_mounts_or_unknown_query_never_become_a_recovery_home(self):
        for code,targets in [(0,'/elsewhere'),(0,'/home /alias'),(2,''),(1,'unexpected')]:
            self.mount_code,self.targets=code,targets
            with self.subTest(code=code,targets=targets),self.assertRaises(RuntimeError):guard.verify_recovery_home(self.cfg,allow_mount=True)
        self.assertEqual(self.started,[])

    def test_readonly_subdirectory_bind_or_duplicate_uuid_device_is_not_the_home(self):
        for mounted in ['test-uuid ro,relatime / /dev/nvme127n1',
                        'test-uuid rw /subdir /dev/nvme127n1',
                        'test-uuid rw / /dev/nvme128n1','other rw / /dev/nvme127n1']:
            self.mounted=mounted
            with self.subTest(mounted=mounted),self.assertRaises(RuntimeError):guard.verify_recovery_home(self.cfg)

    def test_protection_ack_without_authoritative_readback_never_restores(self):
        with patch.object(guard,'protection') as protect,patch.object(guard,'group_state',return_value={'Instances':[{'InstanceId':'i-test','ProtectedFromScaleIn':False}]}):
            with self.assertRaises(RuntimeError):guard.RecoveryOperations(self.cfg,None).protect()
            protect.assert_called_once_with(self.cfg,True)
        self.assertEqual(self.started,[])


class MaintenanceTests(unittest.TestCase):
    def test_running_or_failed_maintenance_blocks_even_without_queued_job(self):
        for states in ['active inactive inactive','inactive failed inactive','activating inactive inactive']:
            with self.subTest(states=states),patch.object(guard,'command',side_effect=['',states]):
                self.assertTrue(guard.maintenance_running())

    def test_unknown_maintenance_is_not_idle(self):
        with patch.object(guard,'command',side_effect=['','inactive']),self.assertRaises(ValueError):guard.maintenance_running()

    def test_queued_maintenance_blocks(self):
        with patch.object(guard,'command',side_effect=['12 nix-gc.service start waiting','inactive inactive inactive']):self.assertTrue(guard.maintenance_running())

    def test_all_inactive_and_no_queue_is_allowed(self):
        with patch.object(guard,'command',side_effect=['','inactive inactive inactive']):self.assertFalse(guard.maintenance_running())


if __name__ == "__main__":
    unittest.main()
