"""Public artifact-work guards only; no extraction/host workload/network here."""
import importlib.util
from pathlib import Path
import tarfile
import unittest

s=importlib.util.spec_from_file_location('extract',Path(__file__).with_name('spot-runtime-extract.py'));p=importlib.util.module_from_spec(s);s.loader.exec_module(p)


class ExtractTests(unittest.TestCase):
    def test_only_two_pinned_public_software_roots_allowed(self):
        for name in ['kiro-cli/bun','openclaw-npm/node/bin/node']:p.member_allowed(tarfile.TarInfo(name))
    def test_private_home_keys_absolute_and_parent_paths_refuse(self):
        for name in ['.ssh/key','home/user/config','/kiro-cli/bun','kiro-cli/../../secret']:
            with self.assertRaises(RuntimeError):p.member_allowed(tarfile.TarInfo(name))
    def test_special_device_or_FIFO_entries_refuse(self):
        for kind in [tarfile.CHRTYPE,tarfile.BLKTYPE,tarfile.FIFOTYPE]:
            member=tarfile.TarInfo('kiro-cli/device');member.type=kind
            with self.assertRaises(RuntimeError):p.member_allowed(member)
    def test_extraction_is_private_artifact_budget_never_verification_success(self):
        source=Path(p.__file__).read_text();self.assertIn("budget['purpose']=='build'",source);self.assertIn('public extraction network must be private',source);self.assertIn('not_verification_or_production_authority',source);self.assertIn('existing public runtime is never overwritten',source)
        self.assertNotIn('canary-build',source);self.assertNotIn('daemon-reload',source)


if __name__=='__main__':unittest.main()
