"""Offline tests. Never invoke AWS or change the running machine."""
import copy
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


class SafetyTests(unittest.TestCase):
    def setUp(self):
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
        with patch.object(guard, "running_window", return_value=True), patch.object(guard, "protection") as protection, patch.object(guard, "command") as command, patch.object(guard, "RUNTIME") as runtime, patch.object(guard.subprocess, "run"):
            with self.assertRaises(RuntimeError):
                guard.drain(self.config)
            command.assert_not_called()
            protection.assert_called_once_with(self.config, True)


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


class FailureTests(unittest.TestCase):
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
        cfg = {"uid":1001,"home_volume":"vol-test"}
        with patch.object(guard, "RUNTIME"), patch.object(guard, "running_window", return_value=False), patch.object(guard, "group_state", return_value={"DesiredCapacity":0}), patch.object(guard, "sessions", return_value=[]), patch.object(guard, "command"), patch.object(guard.subprocess, "run", return_value=SimpleNamespace(returncode=1)) as run, patch.object(guard, "aws", side_effect=RuntimeError("snapshot failed")), patch.object(guard, "protection") as protection:
            with self.assertRaises(RuntimeError):
                guard.drain(cfg)
            protection.assert_called_once_with(cfg, True)
            self.assertTrue(any(c.args[0][:3] == ["systemctl","start","home.mount"] for c in run.call_args_list))

    def test_truthy_non_boolean_arming_does_not_arm(self):
        case = SafetyTests()
        case.setUp()
        for value in ["true", "false", 1, None]:
            with self.subTest(value=value):
                case.config["armed"] = value
                self.assertIn("observation_mode", case.reasons())


if __name__ == "__main__":
    unittest.main()
