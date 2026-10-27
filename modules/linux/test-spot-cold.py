"""Cold block custody unit tests. No real devices, models, services or AWS APIs."""
from contextlib import ExitStack
import importlib.util
import os
from pathlib import Path
import stat
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch
import uuid

spec = importlib.util.spec_from_file_location('cold', Path(__file__).with_name('spot_cold.py'))
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
UUID = '00000000-0000-0000-0000-000000000001'


def superblock():
    data = bytearray(1024)
    struct.pack_into('<HH', data, 0x38, 0xef53, 1)
    struct.pack_into('<II', data, 0x5c, 4, 0x40)
    data[0x68:0x78] = uuid.UUID(UUID).bytes
    return bytes(data)


class FilesystemMetadataTests(unittest.TestCase):
    def test_known_clean_journalled_ext4_uuid(self):
        self.assertEqual(c.filesystem_uuid(superblock()), UUID)

    def test_dirty_recovery_or_unknown_state_is_not_cold(self):
        for state in [0, 2, 3, 5, 0xffff]:
            data=bytearray(superblock());struct.pack_into('<H',data,0x3a,state)
            with self.subTest(state=state),self.assertRaises(c.Unsafe):c.filesystem_uuid(data)
        data=bytearray(superblock());struct.pack_into('<I',data,0x60,0x44)
        with self.assertRaises(c.Unsafe):c.filesystem_uuid(data)

    def test_not_ext4_not_journalled_or_truncated_fails_closed(self):
        for offset,value in [(0x38,0),(0x5c,0),(0x60,0)]:
            data=bytearray(superblock());struct.pack_into('<I' if offset>=0x5c else '<H',data,offset,value)
            with self.subTest(offset=offset),self.assertRaises(c.Unsafe):c.filesystem_uuid(data)
        with self.assertRaises(c.Unsafe):c.filesystem_uuid(b'')


class ClaimTests(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.info=SimpleNamespace(st_mode=stat.S_IFBLK|0o600,st_rdev=123)
        self.stack.enter_context(patch.object(c.Path,'is_symlink',return_value=False))
        self.path_stat=self.stack.enter_context(patch.object(c.Path,'lstat',return_value=self.info))
        self.stack.enter_context(patch.object(c.Path,'read_text',return_value='7\n'))
        self.open=self.stack.enter_context(patch.object(c.os,'open',return_value=55))
        self.close=self.stack.enter_context(patch.object(c.os,'close'))
        self.stat=self.stack.enter_context(patch.object(c.os,'fstat',return_value=self.info))
        self.flush=self.stack.enter_context(patch.object(c.os,'fsync'))
        self.read=self.stack.enter_context(patch.object(c.os,'pread',return_value=superblock()))
        self.flags=self.stack.enter_context(patch.object(c.fcntl,'fcntl',side_effect=lambda fd,op:c.fcntl.FD_CLOEXEC if op==c.fcntl.F_GETFD else os.O_RDONLY))
        def ioctl(fd,op,buffer,mutate):
            self.assertEqual(op,c.BLKGETDISKSEQ);buffer[:]=struct.pack('=Q',7)
        self.ioctl=self.stack.enter_context(patch.object(c.fcntl,'ioctl',side_effect=ioctl))
        self.identity=Mock();self.writers=Mock()
        self.claim=c.FilesystemClaim('/dev/test-block',UUID,identity=self.identity,writers=self.writers)

    def test_readonly_exclusive_no_follow_close_on_exec_and_same_fd_held(self):
        with self.claim:
            self.open.assert_called_once_with(Path('/dev/test-block'),os.O_RDONLY|os.O_EXCL|os.O_CLOEXEC|os.O_NOFOLLOW|os.O_NONBLOCK)
            self.close.assert_not_called();self.claim.check()
            self.flush.assert_called_once_with(55);self.writers.assert_called_with(123)
        self.close.assert_called_once_with(55)

    def test_busy_never_retries_or_changes_device_flags(self):
        self.open.side_effect=BlockingIOError('mounted in another namespace')
        with self.assertRaises(BlockingIOError):self.claim.__enter__()
        self.open.assert_called_once();self.flush.assert_not_called();self.close.assert_not_called()

    def test_failed_attestation_closes_the_claim(self):
        self.writers.side_effect=c.Unsafe('test-only raw writer')
        with self.assertRaises(c.Unsafe):self.claim.__enter__()
        self.close.assert_called_once_with(55);self.flush.assert_not_called()

    def test_uuid_mismatch_never_attests(self):
        data=bytearray(superblock());data[0x68:0x78]=uuid.UUID(int=2).bytes;self.read.return_value=bytes(data)
        with self.assertRaises(c.Unsafe):self.claim.__enter__()
        self.close.assert_called_once_with(55)

    def test_symlink_or_regular_file_cannot_be_used_as_a_device(self):
        self.path_stat.return_value=SimpleNamespace(st_mode=stat.S_IFREG|0o600,st_rdev=0)
        with self.assertRaises(c.Unsafe):self.claim.__enter__()
        self.open.assert_not_called()
        with patch.object(c.Path,'is_symlink',return_value=True),self.assertRaises(c.Unsafe):c.FilesystemClaim('/dev/test-block',UUID)

    def test_changed_device_or_disk_generation_is_unknown(self):
        with self.claim:
            with patch.object(c.Path,'read_text',return_value='8'),self.assertRaises(c.Unsafe):self.claim.check()
            self.path_stat.return_value=SimpleNamespace(st_mode=stat.S_IFBLK,st_rdev=124)
            with self.assertRaises(c.Unsafe):self.claim.check()

    def test_closed_or_forked_claim_cannot_be_used(self):
        self.claim.__enter__()
        self.claim._owner=-1
        with self.assertRaises(c.Unsafe):self.claim.check()
        self.claim.close()
        with self.assertRaises(c.Unsafe):self.claim.check()

    def test_writable_or_inheritable_descriptor_is_not_accepted(self):
        self.flags.side_effect=lambda fd,op:c.fcntl.FD_CLOEXEC if op==c.fcntl.F_GETFD else os.O_RDWR
        with self.assertRaises(c.Unsafe):self.claim.__enter__()
        self.flags.side_effect=lambda fd,op:0
        with self.assertRaises(c.Unsafe):self.claim.__enter__()

    def test_reentering_an_existing_claim_is_refused(self):
        with self.claim:
            with self.assertRaises(c.Unsafe):self.claim.__enter__()
        self.open.assert_called_once()


class WriterObserverTests(unittest.TestCase):
    def setUp(self):
        self.proc=MagicMock();self.proc.__truediv__.return_value.read_text.return_value='systemd'
        self.process=MagicMock();self.process.name='123'
        self.entry=MagicMock();self.entry.name='4'
        self.entry.stat.return_value=SimpleNamespace(st_mode=stat.S_IFBLK,st_rdev=123)
        self.process.__truediv__.return_value.iterdir.return_value=[self.entry]
        self.process.__truediv__.return_value.__truediv__.return_value.read_text.return_value='flags:\t0100000\n'
        self.proc.iterdir.return_value=[self.process]
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(c.os,'geteuid',return_value=0))
        self.stack.enter_context(patch.object(c.os,'readlink',return_value='pid:[host]'))

    def test_readonly_same_device_descriptor_is_not_a_writer(self):
        c.raw_writers(123,self.proc)

    def test_writeonly_or_readwrite_same_device_is_blocked(self):
        for flags in ['0100001','0100002','0100003']:
            self.process.__truediv__.return_value.__truediv__.return_value.read_text.return_value='flags:\t'+flags+'\n'
            with self.subTest(flags=flags),self.assertRaises(c.Unsafe):c.raw_writers(123,self.proc)

    def test_other_devices_or_regular_files_are_not_private_payload_reads(self):
        self.entry.stat.return_value=SimpleNamespace(st_mode=stat.S_IFREG,st_rdev=0)
        c.raw_writers(123,self.proc)
        self.process.__truediv__.return_value.__truediv__.return_value.read_text.assert_not_called()

    def test_permission_denied_or_malformed_fdinfo_is_not_absence(self):
        self.entry.stat.side_effect=PermissionError('unknown process access')
        with self.assertRaises(PermissionError):c.raw_writers(123,self.proc)
        self.entry.stat.side_effect=None
        self.process.__truediv__.return_value.__truediv__.return_value.read_text.return_value='flags:\tinvalid\n'
        with self.assertRaises(ValueError):c.raw_writers(123,self.proc)

    def test_incomplete_process_view_is_not_global_writer_proof(self):
        with patch.object(c.os,'readlink',side_effect=['pid:[child]','pid:[host]']),self.assertRaises(c.Unsafe):c.raw_writers(123,self.proc)


if __name__=='__main__':unittest.main()
