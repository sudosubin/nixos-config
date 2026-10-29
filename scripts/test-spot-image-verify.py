"""Pure offline resolver/privacy/closure cases, not real image or AWS proof."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

s=importlib.util.spec_from_file_location('image_verify',Path(__file__).with_name('spot-image-verify.py'));p=importlib.util.module_from_spec(s);s.loader.exec_module(p)


class VerifyTests(unittest.TestCase):
    def test_target_absolute_symlink_never_reads_host_etc(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'etc').mkdir();(root/'nix/store/abc').mkdir(parents=True);(root/'etc/static').symlink_to('/nix/store/abc');self.assertEqual(p.inside(root,'etc/static/file'),root/'nix/store/abc/file')
    def test_escape_and_symlink_cycles_refuse(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'bad').symlink_to('../../etc');(root/'loop').symlink_to('loop')
            for path in ['bad/passwd','loop']:
                with self.assertRaises(RuntimeError):p.inside(root,path)
    def test_canonical_actual_json_format_one_mapping_is_supported(self):
        source={'/nix/store/path':{'narHash':'sha256-example'}};self.assertEqual(p.closure_rows(source),{'/nix/store/path':'sha256-example'});self.assertNotIn('path',source['/nix/store/path'])
    def test_unknown_duplicate_or_outside_closure_refuses(self):
        for value in [{},[],{'/outside':{'narHash':'sha256-example'}},[{'path':'/nix/store/path','narHash':'sha256-example'}]*2]:
            with self.assertRaises(RuntimeError):p.closure_rows(value)
    def test_empty_image_privacy_is_not_host_privacy(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'etc').mkdir();(root/'etc/machine-id').write_bytes(b'');self.assertEqual(p.privacy(root)['etc/machine-id'],'absent-or-uninitialized')
            (root/'etc/machine-id').write_text('old-machine')
            with self.assertRaises(RuntimeError):p.privacy(root)
    def test_copied_registration_blocks_image(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'var/lib/amazon/ssm').mkdir(parents=True);(root/'var/lib/amazon/ssm/registration').write_text('do not copy')
            with self.assertRaises(RuntimeError):p.privacy(root)


if __name__=='__main__':unittest.main()
