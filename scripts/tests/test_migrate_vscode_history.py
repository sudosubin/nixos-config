import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "migration", Path(__file__).parents[1] / "migrate-vscode-history.py"
)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class HistoryMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "Cursor" / "History"
        self.source.mkdir(parents=True)
        self.other = self.root / "Kiro" / "History"
        self.other.mkdir(parents=True)
        self.destination = self.root / "VSCodium" / "History"
        self.audit = self.root / "audit"
        self.uri = "file:///tmp/example.ts"

    def bucket(self, root, uri, snapshots):
        folder = root / migration.history_hash(uri)
        folder.mkdir(parents=True, exist_ok=True)
        entries = []
        for name, timestamp, content, extra in snapshots:
            (folder / name).write_bytes(content)
            entries.append({"id": name, "timestamp": timestamp, **extra})
        (folder / "entries.json").write_text(
            json.dumps({"version": 1, "resource": uri, "entries": entries})
        )
        return folder

    def apply(self, **kwargs):
        return migration.migrate(
            [self.source, self.other],
            self.destination,
            apply=True,
            audit_dir=self.audit,
            **kwargs,
        )

    def events(self):
        records, _, _ = migration.load_history(self.destination, {}, (), None)
        return {
            (r["resource"], r["metadata"]["timestamp"], r["path"].read_bytes())
            for r in records
        }

    def test_dry_run_never_creates_destination_or_audit(self):
        self.bucket(self.source, self.uri, [("abcd.ts", 1, b"one", {})])
        report = migration.migrate([self.source], self.destination)
        self.assertFalse(report["applied"])
        self.assertEqual(report["output_snapshots"], 1)
        self.assertFalse(self.destination.exists())
        self.assertFalse(self.audit.exists())

    def test_merge_preserves_target_events_and_rolls_back_without_overwrite(self):
        original = self.bucket(
            self.destination, self.uri, [("abcd.ts", 1, b"existing", {})]
        )
        original_metadata = (original / "entries.json").read_bytes()
        self.bucket(self.source, self.uri, [("abcd.ts", 2, b"cursor", {})])
        self.bucket(self.other, self.uri, [("ABCD.ts", 3, b"kiro", {})])
        report = self.apply()
        self.assertEqual(report["output_snapshots"], 3)
        self.assertEqual(len(self.events()), 3)
        rollback = Path(report["rollback"]) / migration.history_hash(self.uri)
        self.assertEqual((rollback / "entries.json").read_bytes(), original_metadata)
        names = [
            r["id"]
            for r in json.loads(
                (
                    self.destination / migration.history_hash(self.uri) / "entries.json"
                ).read_text()
            )["entries"]
        ]
        self.assertEqual(len({n.casefold() for n in names}), 3)
        self.assertTrue(all(len(n) == 7 and n.endswith(".ts") for n in names))

    def test_deduplication_is_idempotent_but_different_times_are_kept(self):
        self.bucket(
            self.source,
            self.uri,
            [("abcd.ts", 1, b"same", {}), ("efgh.ts", 2, b"same", {})],
        )
        self.bucket(self.other, self.uri, [("ijkl.ts", 1, b"same", {})])
        first = self.apply()
        second = self.apply()
        self.assertEqual(first["output_snapshots"], 2)
        self.assertEqual(first["deduplicated_events"], 1)
        self.assertEqual(second["output_snapshots"], 2)
        self.assertEqual(len(self.events()), 2)

    def test_preserve_different_source_metadata(self):
        self.bucket(
            self.source,
            self.uri,
            [
                (
                    "abcd.ts",
                    1,
                    b"same",
                    {"source": "rename", "sourceDescription": "before"},
                )
            ],
        )
        self.bucket(
            self.other,
            self.uri,
            [
                (
                    "abcd.ts",
                    1,
                    b"same",
                    {"source": "rename", "sourceDescription": "after"},
                )
            ],
        )
        self.assertEqual(self.apply()["output_snapshots"], 2)

    def test_unindexed_snapshot_recovery_preserves_bytes_and_mtime(self):
        folder = self.bucket(self.source, self.uri, [])
        file = folder / "Ab12.ts"
        file.write_bytes(b"unindexed")
        import os

        os.utime(file, ns=(1234567890000000, 1234567890000000))
        report = self.apply()
        self.assertEqual(len(report["recovered_unindexed"]), 1)
        self.assertIn((self.uri, 1234567890, b"unindexed"), self.events())
        self.assertEqual(self.apply()["output_snapshots"], 1)

    def test_missing_metadata_requires_explicit_mapping(self):
        folder = self.bucket(self.source, self.uri, [("abcd.ts", 1, b"snapshot", {})])
        (folder / "entries.json").unlink()
        with self.assertRaises(migration.MigrationError):
            self.apply()
        self.assertFalse(self.destination.exists())
        report = self.apply(resource_map={folder.name: self.uri})
        self.assertEqual(report["output_snapshots"], 1)

    def test_unknown_resource_recovered_to_explicit_file_without_guessing(self):
        folder = self.source / "unknown"
        folder.mkdir()
        (folder / "abcd.json").write_bytes(b"{}")
        recovery = self.root / "recovered"
        report = self.apply(recover_to=recovery)
        self.assertTrue(report["recovered_unindexed"][0]["original_path_unknown"])
        self.assertEqual((recovery / "unknown.json").read_bytes(), b"{}")
        self.assertEqual(
            next(iter(self.events()))[0], (recovery / "unknown.json").as_uri()
        )
        self.assertEqual(self.apply(recover_to=recovery)["output_snapshots"], 1)

    def test_wrong_resource_map_fails_closed(self):
        folder = self.bucket(self.source, self.uri, [("abcd.ts", 1, b"snapshot", {})])
        (folder / "entries.json").unlink()
        with self.assertRaises(migration.MigrationError):
            self.apply(resource_map={folder.name: "file:///tmp/wrong.ts"})

    def test_missing_snapshot_aborts_before_touching_existing_destination(self):
        original = self.bucket(
            self.destination, self.uri, [("aaaa.ts", 0, b"existing", {})]
        )
        folder = self.bucket(self.source, self.uri, [("abcd.ts", 1, b"snapshot", {})])
        (folder / "abcd.ts").unlink()
        with self.assertRaises(migration.MigrationError):
            self.apply()
        self.assertEqual((original / "aaaa.ts").read_bytes(), b"existing")

    def test_path_traversal_is_rejected(self):
        folder = self.bucket(self.source, self.uri, [])
        (folder / "entries.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "resource": self.uri,
                    "entries": [{"id": "../outside.ts", "timestamp": 1}],
                }
            )
        )
        with self.assertRaises(migration.MigrationError):
            self.apply()

    def test_incompatible_schema_is_rejected(self):
        folder = self.bucket(self.source, self.uri, [])
        (folder / "entries.json").write_text(
            json.dumps({"version": 2, "resource": self.uri, "entries": []})
        )
        with self.assertRaises(migration.MigrationError):
            self.apply()

    def test_overlapping_paths_and_symlinks_are_rejected(self):
        with self.assertRaises(migration.MigrationError):
            migration.migrate([self.source], self.source / "nested")
        self.bucket(self.source, self.uri, [("abcd.ts", 1, b"snapshot", {})])
        (self.source / "symlink").symlink_to(self.other, target_is_directory=True)
        with self.assertRaises(migration.MigrationError):
            self.apply()

    def test_concurrent_new_snapshot_aborts_before_publishing(self):
        from unittest.mock import patch

        folder = self.bucket(self.source, self.uri, [("abcd.ts", 1, b"snapshot", {})])
        original_copy = migration.shutil.copy2

        def concurrent_copy(source, target):
            result = original_copy(source, target)
            (folder / "new1.ts").write_bytes(b"concurrent save")
            return result

        with (
            patch.object(migration.shutil, "copy2", side_effect=concurrent_copy),
            self.assertRaises(migration.MigrationError),
        ):
            self.apply()
        self.assertFalse(self.destination.exists())

    def test_failed_publish_restores_original_destination(self):
        from unittest.mock import patch

        self.bucket(self.destination, self.uri, [("aaaa.ts", 0, b"existing", {})])
        self.bucket(self.source, self.uri, [("abcd.ts", 1, b"snapshot", {})])
        original_rename = Path.rename

        def failed_publish(path, target):
            if path.name.startswith(".history-staging-"):
                raise OSError("simulated publish failure")
            return original_rename(path, target)

        with patch.object(Path, "rename", failed_publish), self.assertRaises(OSError):
            self.apply()
        self.assertEqual(self.events(), {(self.uri, 0, b"existing")})
        self.assertFalse(list(self.destination.parent.glob(".history-staging-*")))

    def test_source_files_are_byte_for_byte_unchanged(self):
        self.bucket(self.source, self.uri, [("abcd.ts", 1, b"snapshot", {})])
        before = {p: p.read_bytes() for p in self.source.rglob("*") if p.is_file()}
        self.apply()
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_userdata_uri_rewrite_and_unicode_resources(self):
        old = "vscode-userdata:/Users/test/Library/Application%20Support/Cursor/User/keybindings.json"
        new = old.replace("/Cursor/", "/VSCodium/")
        self.bucket(self.source, old, [("abcd.json", 1, b"[]", {})])
        unicode_uri = "file:///tmp/한글-😀.ts"
        self.bucket(self.other, unicode_uri, [("efgh.ts", 2, b"unicode", {})])
        self.apply(rewrites=[(old, new)])
        self.assertIn((new, 1, b"[]"), self.events())
        self.assertIn((unicode_uri, 2, b"unicode"), self.events())
        # Independently calculated with VS Code's JavaScript string hash.
        self.assertEqual(migration.history_hash("file:///tmp/example.ts"), "-cc8fe0b")
        self.assertEqual(migration.history_hash(unicode_uri), "-56e6470d")


if __name__ == "__main__":
    unittest.main()
