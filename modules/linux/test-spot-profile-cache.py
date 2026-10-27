"""Offline profile-persistence tests. Never invoke Nix, AWS, or live services."""
import base64
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock

spec = importlib.util.spec_from_file_location("cache", Path(__file__).with_name("spot-profile-cache.py"))
cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cache)
SYSTEM = "/nix/store/" + "a" * 32 + "-system"
PROFILE = "/nix/store/" + "b" * 32 + "-profile"
OTHER = "/nix/store/" + "c" * 32 + "-profile"
KEY = "cache:" + base64.b64encode(bytes(32)).decode()


class ValidationTests(unittest.TestCase):
    def test_store_path(self):
        self.assertEqual(cache.store_path(PROFILE), PROFILE)

    def test_rejects_non_store_or_nested_paths(self):
        for value in ["/root/private", PROFILE + "/bin/sh", PROFILE + "\n", PROFILE + "/../other", 1, None]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                cache.store_path(value)

    def test_bad_hash_alphabet(self):
        with self.assertRaises(ValueError):
            cache.store_path("/nix/store/" + "e" * 32 + "-profile")

    def test_public_key(self):
        with patch.object(cache, "trusted_text", return_value=KEY + "\n"):
            self.assertEqual(cache.public_key("key"), KEY)

    def test_invalid_public_keys(self):
        for value in ["", KEY + "\n" + KEY, "cache:AAAA", "cache:invalid!", "cache:" + base64.b64encode(bytes(64)).decode()]:
            with self.subTest(value=value), patch.object(cache, "trusted_text", return_value=value), self.assertRaises(ValueError):
                cache.public_key("key")

    def test_trusted_read_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "target"; target.write_text("private")
            link = Path(root) / "link"; link.symlink_to(target)
            with self.assertRaises(OSError):
                cache.trusted_text(link)

    def test_trusted_read_rejects_wrong_owner(self):
        with tempfile.NamedTemporaryFile() as file:
            with patch.object(cache.os, "fstat", return_value=SimpleNamespace(st_mode=0o100600, st_uid=1001, st_size=1)), self.assertRaises(ValueError):
                cache.trusted_text(file.name)

    def test_trusted_read_rejects_writable_or_exposed_secret(self):
        for mode, secret in [(0o100666, False), (0o100640, True), (0o010600, False)]:
            with tempfile.NamedTemporaryFile() as file, patch.object(cache.os, "fstat", return_value=SimpleNamespace(st_mode=mode, st_uid=0, st_size=1)), self.assertRaises(ValueError):
                cache.trusted_text(file.name, secret=secret)

    def test_list_json(self):
        row = {"path": PROFILE, "narSize": 10}
        self.assertEqual(cache.rows_from_json(json.dumps([row])), [row])

    def test_dict_json(self):
        self.assertEqual(cache.rows_from_json(json.dumps({PROFILE: {"narSize": 10}})), [{"path": PROFILE, "narSize": 10}])

    def test_invalid_closure_metadata(self):
        for data in [[], [{"path": PROFILE, "narSize": True}], [{"path": PROFILE, "narSize": -1}], [{"path": "/root/private", "narSize": 1}]]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                cache.rows_from_json(json.dumps(data))

    def test_home_fallback_blocked(self):
        with patch.object(cache, "command", side_effect=["/", "uuid"]), self.assertRaises(ValueError):
            cache.check_home({"home_uuid": "uuid"})

    def test_foreign_home_blocked(self):
        with patch.object(cache, "command", side_effect=["/home", "wrong"]), self.assertRaises(ValueError):
            cache.check_home({"home_uuid": "uuid"})

    def test_correct_home_allowed(self):
        with patch.object(cache, "command", side_effect=["/home", "uuid"]):
            cache.check_home({"home_uuid": "uuid"})

    def test_atomic_manifest(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "manifest.json"
            cache.publish(path, {"schema": 1, "user_profile": PROFILE})
            self.assertEqual(json.loads(path.read_text())["user_profile"], PROFILE)
            self.assertFalse(path.with_suffix(".tmp").exists())


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.config = {"cache": "/home/persist/nix-closure-cache", "public_key": "/home/persist/key"}
        verifier=patch.object(cache,'verify_missing_cache');self.verifier=verifier.start();self.addCleanup(verifier.stop)
        roots = patch.object(cache, "register_roots")
        roots.start()
        self.addCleanup(roots.stop)

    def test_image_contains_profile_no_cache_needed(self):
        with patch.object(cache, "roots", return_value=(PROFILE, [SYSTEM, PROFILE])), patch.object(cache.subprocess, "run", return_value=SimpleNamespace(returncode=0)), patch.object(Path, "exists", return_value=True), patch.object(cache, "command") as command:
            self.assertEqual(cache.restore(self.config)["state"], "restored")
            command.assert_not_called()

    def test_missing_profile_imports_only_from_signed_persistent_cache(self):
        with patch.object(cache, "roots", return_value=(PROFILE, [SYSTEM, PROFILE])), patch.object(cache.subprocess, "run", return_value=SimpleNamespace(returncode=1)), patch.object(cache, "secure_directory"), patch.object(cache, "public_key", return_value=KEY), patch.object(cache, "command") as command:
            cache.restore(self.config)
            call = command.call_args_list[0].args
            self.assertIn("file:///home/persist/nix-closure-cache", call)
            self.assertIn(KEY, call)
            self.assertNotIn("--no-check-sigs", call)

    def test_valid_image_system_need_not_exist_in_source_cache(self):
        with patch.object(cache, "roots", return_value=(PROFILE, [SYSTEM, PROFILE])), patch.object(cache.subprocess, "run", side_effect=[SimpleNamespace(returncode=0), SimpleNamespace(returncode=1)]), patch.object(Path, "exists", return_value=True), patch.object(cache, "secure_directory"), patch.object(cache, "public_key", return_value=KEY), patch.object(cache, "command") as command:
            cache.restore(self.config)
            copy = command.call_args_list[0].args
            self.assertIn(PROFILE, copy)
            self.assertNotIn(SYSTEM, copy)
            self.assertNotIn("--no-check-sigs", copy)
            self.assertEqual(command.call_args_list[1].args, ("nix-store", "--check-validity", SYSTEM, PROFILE))

    def test_validity_metadata_without_files_still_requires_import(self):
        with patch.object(cache, "roots", return_value=(PROFILE, [SYSTEM, PROFILE])), patch.object(cache.subprocess, "run", return_value=SimpleNamespace(returncode=0)), patch.object(Path, "exists", side_effect=[True, False]), patch.object(cache, "secure_directory"), patch.object(cache, "public_key", return_value=KEY), patch.object(cache, "command") as command:
            cache.restore(self.config)
            self.assertIn(PROFILE, command.call_args_list[0].args)
            self.assertNotIn(SYSTEM, command.call_args_list[0].args)

    def test_profile_change_cancels_restore(self):
        with patch.object(cache, "roots", side_effect=[(PROFILE, [PROFILE]), (OTHER, [OTHER])]), patch.object(cache.subprocess, "run", return_value=SimpleNamespace(returncode=0)), patch.object(Path, "exists", return_value=True), self.assertRaises(RuntimeError):
            cache.restore(self.config)

    def test_import_failure_propagates(self):
        with patch.object(cache, "roots", return_value=(PROFILE, [PROFILE])), patch.object(cache.subprocess, "run", return_value=SimpleNamespace(returncode=1)), patch.object(cache, "secure_directory"), patch.object(cache, "public_key", return_value=KEY), patch.object(cache, "command", side_effect=RuntimeError("import failed")), self.assertRaises(RuntimeError):
            cache.restore(self.config)


class RefreshTests(unittest.TestCase):
    """Wrapper sequencing only. Real crypto/NAR/retention tests are separate."""
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.config={'cache':str(self.base),'secret_key':'secret','manifest':str(self.base/'manifest.json'),'reserve_bytes':8192}
        self.rows=[{'path':p,'narSize':100,'narHash':'sha256:'+('0'*52)} for p in [SYSTEM,PROFILE]]
        self.manager=Mock()
        self.manager.previous.return_value=None;self.manager.adopt.return_value=None
        self.manager.verify_current.side_effect=cache.spot_cache.Unsafe('not current')
        self.manager.entry.side_effect=FileNotFoundError('private missing fixture')
        self.manager.checkpoint.return_value={'id':'a'*32}
        self.manager.cleanup_repairs.return_value=0;self.manager.garbage_pending.return_value=False
        self.patches=[patch.object(cache,'secure_directory',return_value=self.base),
                      patch.object(cache,'ensure_keys',return_value=KEY),
                      patch.object(cache,'roots',return_value=(PROFILE,[SYSTEM,PROFILE])),
                      patch.object(cache.os,'statvfs',return_value=SimpleNamespace(f_bavail=100000,f_frsize=4096)),
                      patch.object(cache,'command',side_effect=[json.dumps(self.rows),'']),
                      patch.object(cache,'register_roots'),
                      patch.object(cache.spot_cache,'Cache',return_value=self.manager)]
        self.mocks=[p.start() for p in self.patches]
        for p in self.patches:self.addCleanup(p.stop)

    def test_core_verified_export_publishes(self):
        result=cache.refresh(self.config)
        self.assertEqual(result['paths'],2);self.assertEqual(result['inventory'],'a'*32)
        self.manager.checkpoint.assert_called_once_with(PROFILE,[SYSTEM,PROFILE],self.rows,parent=None)

    def test_warm_noop_reconciles_repair_left_after_published_checkpoint(self):
        self.manager.verify_current.side_effect=None
        self.manager.verify_current.return_value={'entries':{SYSTEM:{},PROFILE:{}}}
        self.manager.cleanup_repairs.return_value=2
        out=cache.refresh(self.config)
        self.assertEqual(out['state'],'current');self.assertEqual(out['repair_files_removed'],2)
        self.mocks[4].assert_not_called();self.manager.checkpoint.assert_not_called()
        self.manager.cleanup_repairs.assert_called_once()

    def test_low_space_never_completes(self):
        self.mocks[3].return_value=SimpleNamespace(f_bavail=1,f_frsize=1)
        with self.assertRaises(RuntimeError):cache.refresh(self.config)
        self.manager.checkpoint.assert_not_called();self.manager.invalidate.assert_called_once()

    def test_copy_failure_never_completes(self):
        self.mocks[4].side_effect=[json.dumps(self.rows),RuntimeError('copy failed')]
        with self.assertRaises(RuntimeError):cache.refresh(self.config)
        self.manager.checkpoint.assert_not_called();self.manager.invalidate.assert_called()

    def test_invalid_signature_propagates(self):
        self.manager.checkpoint.side_effect=cache.spot_cache.Unsafe('configured signature invalid')
        with self.assertRaises(cache.spot_cache.Unsafe):cache.refresh(self.config)
        self.manager.cleanup_repairs.assert_not_called()

    def test_profile_change_never_cleans_evidence(self):
        self.manager.checkpoint.side_effect=RuntimeError('profile generations changed')
        with self.assertRaises(RuntimeError):cache.refresh(self.config)
        self.manager.cleanup_repairs.assert_not_called()


class GCRootTests(unittest.TestCase):
    def test_nix_registration_api_is_used_for_every_selected_root(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(cache, "secure_directory", return_value=Path(tmp)), patch.object(cache, "command") as command:
            cache.register_roots({"gc_roots":tmp}, [SYSTEM, PROFILE])
            self.assertEqual(command.call_count, 2)
            self.assertIn("--add-root", command.call_args.args)
            self.assertEqual(command.call_args.args[-1], PROFILE)

    def test_unknown_gc_root_file_is_never_removed(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(cache, "secure_directory", return_value=Path(tmp)), patch.object(cache, "command"):
            bad=Path(tmp)/"root-10";bad.write_text("not a symlink")
            with self.assertRaises(ValueError):
                cache.register_roots({"gc_roots":tmp}, [PROFILE])
            self.assertTrue(bad.exists())


if __name__ == "__main__":
    unittest.main()
