"""Real running-kernel cold custody, on strictly identified disposable loop disks.

No EC2/EBS mutation, production device, home, model, credential or app is used.
Every mount is in a private mount/network namespace; keep the host PID view for
raw-writer observations. No skipped case is acceptable as cloud verification.
"""
import errno
import importlib.util
import os
from pathlib import Path
import re
import select
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import unittest
import uuid

spec=importlib.util.spec_from_file_location('cold',Path(__file__).with_name('spot_cold.py'))
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

HOLDER=r'''import os,subprocess,sys
from pathlib import Path
loop,base,mode=sys.argv[1:];base=Path(base);point=base/'hidden';point.mkdir()
subprocess.run(['mount','--make-rprivate','/'],check=True)
subprocess.run(['mount',loop,str(point)],check=True)
file=None;overlay=None
try:
 if mode=='lazy':
  os.chdir(point);file=open('held-file','wb');file.write(b'isolated-loop-only');file.flush();os.fsync(file.fileno())
  subprocess.run(['umount','--lazy',str(point)],check=True)
 if mode=='overlay':
  for name in ['lower','upper','work']:(point/name).mkdir()
  overlay=base/'overlay';overlay.mkdir()
  options=','.join(name+'='+str(point/value) for name,value in [('lowerdir','lower'),('upperdir','upper'),('workdir','work')])
  subprocess.run(['mount','-t','overlay','-o',options,'overlay',str(overlay)],check=True)
  subprocess.run(['umount','--lazy',str(point)],check=True)
  (overlay/'synthetic-write').write_text('only a disposable loop filesystem')
 print('READY',flush=True);sys.stdin.readline()
finally:
 os.chdir('/')
 if file:file.close()
 if overlay:subprocess.run(['umount',str(overlay)],check=True)
 subprocess.run(['umount',str(point)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
'''


@unittest.skipUnless(sys.platform=='linux' and os.geteuid()==0,'explicit root Linux fixture required')
class KernelColdTests(unittest.TestCase):
    def setUp(self):
        self.base=Path(tempfile.mkdtemp(prefix='spot-cold-kernel-',dir='/run'))
        self.image=self.base/'OWN-32MiB-TEST-ONLY.img';self.loop=None;self.children=[];self.mounts=[]
        self.addCleanup(self.cleanup)
        fd=os.open(self.image,os.O_RDWR|os.O_CREAT|os.O_EXCL,0o600)
        try:os.ftruncate(fd,32*1024*1024)
        finally:os.close(fd)
        self.loop=subprocess.check_output(['losetup','--find','--show',str(self.image)],text=True).strip()
        self.assert_owned_loop()
        tools=[p for p in Path('/nix/store').glob('*-e2fsprogs-1.47.4*/bin/mkfs.ext4') if p.is_file()]
        self.assertTrue(tools,'pinned formatter required; skipping is not proof')
        subprocess.run([str(tools[0]),'-q','-F',self.loop],check=True,capture_output=True,timeout=15)
        self.uuid=subprocess.check_output(['blkid','-c','/dev/null','-p','-s','UUID','-o','value',self.loop],text=True).strip()
        self.point=self.base/'visible';self.point.mkdir()

    def assert_owned_loop(self):
        self.assertRegex(self.loop,r'^/dev/loop[0-9]+$')
        self.assertTrue(stat.S_ISBLK(Path(self.loop).lstat().st_mode))
        backing=Path('/sys/class/block',Path(self.loop).name,'loop/backing_file').read_text().strip()
        self.assertEqual(backing,str(self.image));self.assertEqual(self.image.stat().st_size,32*1024*1024)
        self.assertTrue(str(self.image).startswith('/run/spot-cold-kernel-'))

    def cleanup(self):
        for child in self.children:
            if child.poll() is None:
                if child.stdin is not None and not child.stdin.closed:
                    try:child.stdin.close()
                    except BrokenPipeError:pass
                try:child.wait(timeout=5)
                except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
            for stream in [child.stdin,child.stdout,child.stderr]:
                if stream is not None and not stream.closed:stream.close()
        for point in reversed(self.mounts):
            subprocess.run(['umount',str(point)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if self.loop:
            self.assert_owned_loop()
            subprocess.run(['losetup','--detach',self.loop],check=True)
        shutil.rmtree(self.base)

    def mount(self):
        self.assert_owned_loop()
        subprocess.run(['mount',self.loop,str(self.point)],check=True,capture_output=True,timeout=8)
        self.mounts.append(self.point)

    def unmount(self):
        subprocess.run(['umount',str(self.point)],check=True,capture_output=True,timeout=8)
        self.mounts.remove(self.point)

    def claim(self):return c.FilesystemClaim(self.loop,self.uuid)

    def ready(self,child):
        self.assertTrue(select.select([child.stdout],[],[],12)[0],'isolated holder not ready')
        self.assertEqual(child.stdout.readline(),b'READY\n')
        self.assertIsNone(child.poll())

    def hidden(self,mode):
        child=subprocess.Popen(['unshare','--mount','--',sys.executable,'-c',HOLDER,self.loop,str(self.base),mode],
                               stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.children.append(child);self.ready(child)
        # The old namespace-local cold check really would see no mount.
        query=subprocess.run(['findmnt','-rn','-S','UUID='+self.uuid,'-o','TARGET'],capture_output=True)
        self.assertEqual(query.returncode,1);self.assertEqual(query.stdout,b'')
        with self.assertRaises(OSError) as error:self.claim().__enter__()
        self.assertEqual(error.exception.errno,errno.EBUSY)
        child.stdin.close();child.wait(timeout=8);self.assertEqual(child.returncode,0,child.stderr.read())
        with self.claim() as claim:claim.check()

    def test_mount_cannot_race_into_snapshot_window_but_works_before_and_after(self):
        self.mount();self.unmount()
        with self.claim() as claim:
            result=subprocess.run(['mount',self.loop,str(self.point)],capture_output=True,timeout=8)
            self.assertNotEqual(result.returncode,0);claim.check()
        self.mount();self.unmount()

    def test_other_mount_namespace_is_not_cold_despite_empty_findmnt(self):
        self.hidden('mounted')

    def test_detached_lazy_mount_with_open_file_and_cwd_is_not_cold(self):
        self.hidden('lazy')

    def test_overlay_upper_work_references_keep_detached_filesystem_busy(self):
        self.hidden('overlay')

    def test_raw_writer_is_observed_not_falsely_excluded_by_readonly_claim(self):
        with self.claim() as claim:
            # O_EXCL excludes filesystem holders, not privileged raw O_WRONLY.
            # Do not write any bytes; observe the limitation explicitly.
            writer=os.open(self.loop,os.O_WRONLY|os.O_CLOEXEC)
            try:
                with self.assertRaises(c.Unsafe):claim.check()
            finally:os.close(writer)
            claim.check()

    def test_wrong_uuid_closes_claim_before_rollback_mount(self):
        with self.assertRaises(c.Unsafe):
            with c.FilesystemClaim(self.loop,str(uuid.uuid4())):self.fail('wrong UUID accepted')
        self.mount();self.unmount()

    def test_killed_coordinator_automatically_releases_kernel_claim(self):
        code="import importlib.util,sys;from pathlib import Path;s=importlib.util.spec_from_file_location('cold',sys.argv[1]);c=importlib.util.module_from_spec(s);s.loader.exec_module(c);claim=c.FilesystemClaim(sys.argv[2],sys.argv[3]);claim.__enter__();print('READY',flush=True);sys.stdin.readline()"
        child=subprocess.Popen([sys.executable,'-c',code,str(Path(__file__).with_name('spot_cold.py')),self.loop,self.uuid],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.children.append(child);self.ready(child)
        result=subprocess.run(['mount',self.loop,str(self.point)],capture_output=True,timeout=8)
        self.assertNotEqual(result.returncode,0)
        child.kill();child.wait(timeout=5);self.assertEqual(child.returncode,-signal.SIGKILL)
        self.mount();self.unmount()

    def test_claim_is_not_inherited_into_exec_children(self):
        with self.claim():
            child=subprocess.Popen([sys.executable,'-c',"import sys,time;print('READY',flush=True);sys.stdin.readline()"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            self.children.append(child);self.ready(child)
        self.assertIsNone(child.poll())
        self.mount();self.unmount()


if __name__=='__main__':
    if sys.platform=='linux' and os.geteuid()==0 and '--private-cold-test' not in sys.argv:
        sys.exit(subprocess.call(['unshare','--mount','--net','--',sys.executable,str(Path(__file__).resolve()),'--private-cold-test']))
    if '--private-cold-test' in sys.argv:
        sys.argv.remove('--private-cold-test')
        subprocess.run(['mount','--make-rprivate','/'],check=True)
    unittest.main()
