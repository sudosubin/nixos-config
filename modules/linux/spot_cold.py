#!/usr/bin/env python3
"""Enforced filesystem cold custody, not a whole-server idle certificate.

Linux block O_RDONLY|O_EXCL claims conflict with mounts in EVERY mount namespace,
including detached mounts kept alive by cwd/open files/overlay references. Keep
that actual kernel claim through snapshot attestation and the final release.
It does NOT prohibit arbitrary privileged raw I/O: raw writer observations and
complete producer admission remain separate requirements. Never freeze, format,
force-unmount, detach, or change device read-only flags to manufacture cold.
"""
import fcntl
import os
from pathlib import Path
import re
import stat
import struct
import uuid

BLKGETDISKSEQ = 0x80081280
VOLUME = re.compile(r'^vol-[0-9a-f]{8,17}$')


class Unsafe(RuntimeError):
    pass


def filesystem_uuid(superblock):
    if len(superblock) != 1024:
        raise Unsafe('ext4 superblock unavailable')
    magic, state = struct.unpack_from('<HH', superblock, 0x38)
    compat, incompat = struct.unpack_from('<II', superblock, 0x5c)
    if (magic != 0xef53 or state != 1 or incompat & 4
            or not compat & 4 or not incompat & 0x40):
        raise Unsafe('filesystem is not a clean journalled ext4 volume')
    return str(uuid.UUID(bytes=superblock[0x68:0x78]))


def raw_writers(rdev, proc=Path('/proc')):
    # This observer must see the host PID namespace. The kernel filesystem claim
    # itself is namespace-independent. A nested/incomplete process view is not
    # accepted as proof that a privileged raw writer is absent.
    if (os.geteuid() != 0 or (proc/'1/comm').read_text().strip() != 'systemd'
            or os.readlink(proc/'self/ns/pid') != os.readlink(proc/'1/ns/pid')):
        raise Unsafe('host process view unavailable for raw writer observation')
    for process in proc.iterdir():
        if not process.name.isdigit():
            continue
        try:
            entries = list((process/'fd').iterdir())
        except (FileNotFoundError, ProcessLookupError):
            continue  # Task exited, not a skipped live/permission-denied task.
        for entry in entries:
            try:
                info = entry.stat()
                if not stat.S_ISBLK(info.st_mode) or info.st_rdev != rdev:
                    continue
                fields = dict(line.split(':', 1) for line in (process/'fdinfo'/entry.name).read_text().splitlines()
                              if ':' in line)
                flags = int(fields['flags'].strip(), 8)
                if flags & os.O_ACCMODE != os.O_RDONLY:
                    raise Unsafe('raw block writer still owns the source device')
            except (FileNotFoundError, ProcessLookupError):
                continue  # The file was closed; the caller flushes before capture.


class FilesystemClaim:
    def __init__(self, device, expected_uuid, identity=lambda: None, writers=raw_writers):
        self.device, self.expected_uuid = Path(device), expected_uuid
        if (not self.device.is_absolute() or str(uuid.UUID(expected_uuid)) != expected_uuid
                or self.device.is_symlink()):
            raise Unsafe('non-canonical cold device identity')
        self.identity, self.writers = identity, writers
        self._fd = None
        self._owner = None
        self._info = None
        self._sequence = None

    def sequence(self):
        value = bytearray(8)
        fcntl.ioctl(self._fd, BLKGETDISKSEQ, value, True)
        sequence = struct.unpack('=Q', value)[0]
        if sequence <= 0:
            raise Unsafe('block disk generation unknown')
        return sequence

    def __enter__(self):
        if self._fd is not None:
            raise Unsafe('cold device already claimed')
        self.identity()
        before = self.device.lstat()
        if not stat.S_ISBLK(before.st_mode):
            raise Unsafe('cold source is not a block device')
        self._owner = os.getpid()
        # Do not retry EBUSY, force unmount, or freeze another holder. No file
        # descriptor crosses an exec into the AWS CLI or other child programs.
        self._fd = os.open(self.device, os.O_RDONLY | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            self._info = os.fstat(self._fd)
            if self._info.st_rdev != before.st_rdev or not stat.S_ISBLK(self._info.st_mode):
                raise Unsafe('block source changed while claiming')
            self._sequence = self.sequence()
            self.check()
            os.fsync(self._fd)  # Flush this block device, not somebody's filesystem.
            self.check()
            return self
        except BaseException:
            self.close()
            raise

    def check(self):
        if self._fd is None or self._owner != os.getpid():
            raise Unsafe('cold claim is closed or belongs to another process')
        info = os.fstat(self._fd)
        path_info = self.device.lstat()
        if (not stat.S_ISBLK(info.st_mode) or not stat.S_ISBLK(path_info.st_mode)
                or info.st_rdev != self._info.st_rdev or path_info.st_rdev != info.st_rdev
                or self.sequence() != self._sequence
                or int(Path('/sys/class/block', self.device.name, 'diskseq').read_text().strip()) != self._sequence
                or fcntl.fcntl(self._fd, fcntl.F_GETFL) & os.O_ACCMODE != os.O_RDONLY
                or not fcntl.fcntl(self._fd, fcntl.F_GETFD) & fcntl.FD_CLOEXEC):
            raise Unsafe('cold device or generation changed')
        self.identity()
        self.writers(info.st_rdev)
        if filesystem_uuid(os.pread(self._fd, 1024, 1024)) != self.expected_uuid:
            raise Unsafe('claimed filesystem UUID changed')

    def close(self):
        if self._fd is not None:
            fd, self._fd = self._fd, None
            os.close(fd)

    def __exit__(self, *error):
        self.close()


def configured(config):
    volume, expected_uuid = config['home_volume'], config['home_uuid']
    if not isinstance(volume, str) or not VOLUME.fullmatch(volume):
        raise Unsafe('invalid exact EBS identity')
    serial = volume.replace('-', '')
    matches = [p for p in Path('/sys/class/block').glob('nvme*n1/device/serial')
               if p.read_text().strip() == serial]
    if len(matches) != 1:
        raise Unsafe('expected EBS serial is missing or ambiguous')
    serial_file = matches[0]
    device = Path('/dev') / serial_file.parent.parent.name
    def identity():
        if (serial_file.read_text().strip() != serial
                or Path('/dev/disk/by-uuid', expected_uuid).resolve() != device):
            raise Unsafe('EBS serial/UUID alias changed')
    return FilesystemClaim(device, expected_uuid, identity=identity)
