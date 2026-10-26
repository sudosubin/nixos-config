"""Offline profile-persistence tests. Never invoke Nix, AWS, or live services."""
import base64
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

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

    def test_profile_change_cancels_restore(self):
        with patch.object(cache, "roots", side_effect=[(PROFILE, [PROFILE]), (OTHER, [OTHER])]), patch.object(cache.subprocess, "run", return_value=SimpleNamespace(returncode=0)), patch.object(Path, "exists", return_value=True), self.assertRaises(RuntimeError):
            cache.restore(self.config)

    def test_import_failure_propagates(self):
        with patch.object(cache, "roots", return_value=(PROFILE, [PROFILE])), patch.object(cache.subprocess, "run", return_value=SimpleNamespace(returncode=1)), patch.object(cache, "secure_directory"), patch.object(cache, "public_key", return_value=KEY), patch.object(cache, "command", side_effect=RuntimeError("import failed")), self.assertRaises(RuntimeError):
            cache.restore(self.config)


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.config = {"cache": str(self.base), "secret_key": "secret", "manifest": str(self.base / "manifest.json"), "reserve_bytes": 8192}
        self.row = {"path": PROFILE, "narSize": 100}
        self.patches = [
            patch.object(cache, "secure_directory", return_value=self.base),
            patch.object(cache, "ensure_keys", return_value=KEY),
            patch.object(cache, "roots", return_value=(PROFILE, [SYSTEM, PROFILE])),
            patch.object(cache.os, "statvfs", return_value=SimpleNamespace(f_bavail=100000, f_frsize=4096)),
            patch.object(cache, "command", side_effect=[json.dumps([self.row]), ""]),
            patch.object(cache, "trusted_text", return_value="Sig: cache:signature\n"),
            patch.object(cache, "register_roots"),
            patch.object(cache.os.path, "realpath", return_value=SYSTEM),
            patch.object(cache, "publish"),
        ]
        self.mocks = [p.start() for p in self.patches]
        for p in self.patches:
            self.addCleanup(p.stop)

    def test_complete_signed_export_publishes(self):
        result = cache.refresh(self.config)
        self.assertEqual(result["paths"], 1)
        manifest = self.mocks[-1].call_args.args[1]
        self.assertEqual(manifest["schema"], 1)
        self.assertEqual(manifest["user_profile"], PROFILE)

    def test_low_space_never_publishes(self):
        self.mocks[3].return_value = SimpleNamespace(f_bavail=1, f_frsize=1)
        with self.assertRaises(RuntimeError):
            cache.refresh(self.config)
        self.mocks[-1].assert_not_called()

    def test_copy_failure_never_publishes(self):
        self.mocks[4].side_effect = [json.dumps([self.row]), RuntimeError("copy failed")]
        with self.assertRaises(RuntimeError):
            cache.refresh(self.config)
        self.mocks[-1].assert_not_called()

    def test_missing_signature_never_publishes(self):
        self.mocks[5].return_value = "Sig: another:signature\n"
        with self.assertRaises(ValueError):
            cache.refresh(self.config)
        self.mocks[-1].assert_not_called()

    def test_profile_change_never_publishes(self):
        self.mocks[2].side_effect = [(PROFILE, [SYSTEM, PROFILE]), (OTHER, [SYSTEM, OTHER])]
        with self.assertRaises(RuntimeError):
            cache.refresh(self.config)
        self.mocks[-1].assert_not_called()


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
