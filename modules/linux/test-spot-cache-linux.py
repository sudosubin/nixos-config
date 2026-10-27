#!/usr/bin/env python3
"""Actual private Nix stores/cache/Ed25519/GC; never touch the live cache/store.

Root only. Private PID/mount/network namespaces, empty /home and /root, readonly
/nix, sanitized environment, fresh fixture signing keys, NoNewPrivileges. These
are rooted private-store tests, NOT a real image boot, OS reboot or production
rollout. All logical paths and GC registrations are exercised by actual Nix.
"""
import argparse
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).parent
import spot_cache
spec=importlib.util.spec_from_file_location('profile_cache',HERE/'spot-profile-cache.py')
profile_cache=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile_cache)


class NativeCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='case-',dir='/home/persist')
        self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.source=self.root/'source';self.destination=self.root/'destination'
        self.home=self.root/'home';self.home.mkdir();self.conf=self.root/'nix-conf';self.conf.mkdir()
        self.environment={'PATH':os.environ['PATH'],'HOME':str(self.home),'TMPDIR':'/tmp',
                          'NIX_CONF_DIR':str(self.conf),'NIX_USER_CONF_FILES':'',
                          'NIX_CONFIG':'experimental-features = nix-command flakes\nsubstituters =\nrequire-sigs = true\n',
                          'AWS_EC2_METADATA_DISABLED':'true','NIX_REMOTE':'local?root='+str(self.source)}
        self.previous_environment=dict(os.environ);os.environ.clear();os.environ.update(self.environment)
        self.addCleanup(self.restore_environment)
        self.config={'cache':str(self.root/'cache'),'manifest':str(self.root/'manifest.json'),
                     'public_key':str(self.root/'public'),'secret_key':str(self.root/'secret'),
                     'gc_roots':str(self.root/'gc-roots'),'reserve_bytes':8*1024*1024,
                     'system_profile':str(self.root/'system'),'profile':str(self.root/'profile'),
                     'home_profile':str(self.root/'missing-hm'),'generation_directories':[str(self.root/'generations')],
                     'keep_checkpoints':2,'prune_grace_seconds':0,'uid':0}
        self.generations=self.root/'generations';self.generations.mkdir()
        self.system=self.add('system',b'fixture-system')
        self.package=self.add('profile',b'fixture-profile')
        self.old=self.add('old-profile',b'fixture-retained-generation')
        (self.root/'system').symlink_to(self.system);(self.root/'profile').symlink_to(self.package)
        (self.generations/'profile-1-link').symlink_to(self.old)

    def restore_environment(self):
        os.environ.clear();os.environ.update(self.previous_environment)

    def run_nix(self,*args):
        result=subprocess.run(args,text=True,capture_output=True,timeout=90)
        if result.returncode:raise RuntimeError('fixture Nix failed: '+result.stderr)
        return result.stdout.strip()

    def add(self,name,contents):
        directory=self.root/('input-'+name);directory.mkdir()
        p=directory/'fixture';p.write_bytes(contents)
        return self.run_nix('nix-store','--add',str(directory))

    def rows(self,paths):
        return profile_cache.rows_from_json(self.run_nix('nix','path-info','--recursive','--json','--json-format','1',*paths))

    def manager(self):
        return spot_cache.Cache(self.config,profile_cache.public_key(self.config['public_key']),
                                profile_cache.command,lambda:profile_cache.roots(self.config))

    def export(self):
        result=profile_cache.refresh(self.config)
        self.assertIn(result['state'],['cached','current']);return result

    def test_actual_signed_export_all_retained_generations_empty_store_restore_and_gc(self):
        self.export();manager=self.manager();manager.verify_current()
        self.assertIn(self.old,manager.previous()['roots'])
        self.run_nix('nix-store','--gc')
        for path in [self.system,self.package,self.old]:self.run_nix('nix-store','--check-validity',path)
        os.environ['NIX_REMOTE']='local?root='+str(self.destination)
        result=profile_cache.restore(self.config);self.assertEqual(result['roots'],3)
        for path,data in [(self.system,b'fixture-system'),(self.package,b'fixture-profile'),(self.old,b'fixture-retained-generation')]:
            self.assertEqual((self.destination/path.lstrip('/')/'fixture').read_bytes(),data)
        self.run_nix('nix-store','--gc')
        for path in [self.system,self.package,self.old]:self.run_nix('nix-store','--check-validity',path)

    def test_actual_same_name_forged_signature_refused_before_nix_import(self):
        self.export();manager=self.manager();p=manager.info_path(self.package)
        lines=p.read_text().splitlines();lines=[('Sig: nixos-ec2-persist:'+('A'*86)+'==') if x.startswith('Sig: nixos-ec2-persist:') else x for x in lines]
        p.write_text('\n'.join(lines)+'\n')
        os.environ['NIX_REMOTE']='local?root='+str(self.destination)
        with self.assertRaises(spot_cache.Unsafe):profile_cache.restore(self.config)
        result=subprocess.run(['nix-store','--check-validity',self.package],capture_output=True)
        self.assertNotEqual(result.returncode,0)

    def test_actual_corrupt_compressed_body_invalidates_then_repairs_from_source(self):
        self.export();manager=self.manager();entry=manager.entry(self.package);file=manager.cache/entry['url']
        data=file.read_bytes();file.write_bytes(bytes([data[0]^1])+data[1:])
        with self.assertRaises(spot_cache.Unsafe):profile_cache.verify(self.config)
        self.assertEqual(manager.current()['state'],'unverified')
        self.export();self.manager().verify_current();self.assertFalse(any(manager.quarantine.iterdir()))
        os.environ['NIX_REMOTE']='local?root='+str(self.destination)
        profile_cache.restore(self.config)
        self.assertEqual((self.destination/self.package.lstrip('/')/'fixture').read_bytes(),b'fixture-profile')

    def test_actual_retention_preserves_every_retained_generation_then_prunes_obsolete_only(self):
        self.export();manager=self.manager();old_entry=manager.entry(self.old)
        # More checkpoints alone NEVER permit deleting a user-retained generation.
        profile,paths=profile_cache.roots(self.config)
        rows=self.rows(paths)
        parent=manager.previous();parent=manager.checkpoint(profile,paths,rows,parent=parent['id'])
        manager.checkpoint(profile,paths,rows,parent=parent['id']);manager.prune()
        self.assertTrue(manager.info_path(self.old).exists())
        (self.generations/'profile-1-link').unlink()  # fixture user explicitly wipes this generation
        self.export();self.assertTrue(manager.info_path(self.old).exists())  # previous checkpoint still protects it
        profile,paths=profile_cache.roots(self.config)
        rows=self.rows(paths)
        manager.checkpoint(profile,paths,rows,parent=manager.previous()['id'])
        self.assertTrue(manager.garbage_pending());out=manager.prune()
        self.assertEqual(out['narinfos_removed'],1);self.assertEqual(out['nar_objects_removed'],1)
        self.assertFalse((manager.cache/old_entry['url']).exists());manager.verify_current()

    def test_actual_low_space_and_export_interruption_never_complete_or_lose_previous_data(self):
        self.export();manager=self.manager();old_entry=manager.entry(self.package)
        new=self.add('new-package',b'fixture-new');(self.generations/'profile-2-link').symlink_to(new)
        self.config['reserve_bytes']=2**62
        with self.assertRaises(RuntimeError):profile_cache.refresh(self.config)
        self.assertEqual(manager.current()['state'],'unverified')
        self.assertEqual(manager.entry(self.package),old_entry)
        self.config['reserve_bytes']=8*1024*1024
        original=profile_cache.command
        def fail_export(*args,**kwargs):
            if 'copy' in args and '--to' in args:raise RuntimeError('private fixture export interruption')
            return original(*args,**kwargs)
        profile_cache.command=fail_export
        try:
            with self.assertRaises(RuntimeError):profile_cache.refresh(self.config)
        finally:profile_cache.command=original
        self.assertEqual(manager.current()['state'],'unverified');self.assertEqual(manager.entry(self.package),old_entry)
        self.export();self.manager().verify_current()

    def test_actual_lost_signing_key_never_rotates_and_public_metadata_recovers_readonly_import(self):
        self.export();manager=self.manager();key=profile_cache.public_key(self.config['public_key'])
        Path(self.config['secret_key']).unlink();Path(self.config['public_key']).unlink()
        with self.assertRaisesRegex(ValueError,'refusing implicit rotation'):profile_cache.refresh(self.config)
        self.assertFalse(Path(self.config['secret_key']).exists());self.assertFalse(Path(self.config['public_key']).exists())
        os.environ['NIX_REMOTE']='local?root='+str(self.destination)
        profile_cache.restore(self.config)
        self.assertEqual(profile_cache.public_key(self.config['public_key']),key)
        self.assertEqual((self.destination/self.package.lstrip('/')/'fixture').read_bytes(),b'fixture-profile')
        with self.assertRaises(FileNotFoundError):profile_cache.verify(self.config)
        self.assertEqual(manager.current()['state'],'unverified')
        self.assertFalse(Path(self.config['secret_key']).exists())

    def test_actual_mismatched_signer_defers_readiness_without_overwriting_valid_cached_data(self):
        self.export();manager=self.manager();expected=manager.entry(self.package)
        secret=Path(self.config['secret_key']);saved=self.root/'saved-secret';secret.rename(saved)
        self.run_nix('nix-store','--generate-binary-cache-key','nixos-ec2-persist',str(secret),str(self.root/'other-public'))
        secret.chmod(0o600)
        with self.assertRaisesRegex(ValueError,'keys disagree'):profile_cache.verify(self.config)
        self.assertEqual(manager.current()['state'],'unverified');self.assertEqual(manager.entry(self.package),expected)
        with self.assertRaisesRegex(ValueError,'keys disagree'):profile_cache.refresh(self.config)
        saved.replace(secret);self.export();self.manager().verify_current()

    def test_actual_recompressed_retained_path_reclaims_old_encoding_not_live_metadata(self):
        self.export();manager=self.manager();first=manager.previous();old=manager.entry(self.package)
        manager.info_path(self.package).rename(self.root/'saved-fixture-narinfo')
        uri='file://'+self.config['cache']+'?compression=xz&compression-level=0&secret-key='+self.config['secret_key']
        self.run_nix('nix','--option','narinfo-cache-positive-ttl','0','copy','--to',uri,self.package)
        encoded=manager.entry(self.package);self.assertNotEqual(encoded['url'],old['url'])
        self.assertEqual(spot_cache.parse(encoded['narinfo'])['NarHash'],spot_cache.parse(old['narinfo'])['NarHash'])
        profile,paths=profile_cache.roots(self.config);rows=self.rows(paths)
        second=manager.checkpoint(profile,paths,rows,parent=first['id'])
        self.assertEqual(manager.prune()['nar_objects_removed'],0)  # BOTH representations still protected
        manager.checkpoint(profile,paths,rows,parent=second['id'])
        self.assertTrue(manager.garbage_pending());out=manager.prune()
        self.assertEqual(out['narinfos_removed'],0);self.assertEqual(out['nar_objects_removed'],1)
        self.assertFalse((manager.cache/old['url']).exists());self.assertTrue((manager.cache/encoded['url']).exists())
        os.environ['NIX_REMOTE']='local?root='+str(self.destination);profile_cache.restore(self.config)
        self.assertEqual((self.destination/self.package.lstrip('/')/'fixture').read_bytes(),b'fixture-profile')

    def test_actual_shared_nar_body_is_not_deleted_with_one_retired_path(self):
        self.export();manager=self.manager()
        shared=self.add('shared-name',b'fixture-profile')
        # --add includes directory root names only in the store path, not NAR bytes.
        (self.generations/'profile-2-link').symlink_to(shared);self.export()
        first=manager.entry(shared);current=manager.entry(self.package)
        self.assertEqual(first['url'],current['url'])
        (self.generations/'profile-2-link').unlink();self.export()
        profile,paths=profile_cache.roots(self.config)
        rows=self.rows(paths)
        manager.checkpoint(profile,paths,rows,parent=manager.previous()['id'])
        out=manager.prune();self.assertEqual(out['narinfos_removed'],1)
        self.assertEqual(out['nar_objects_removed'],0);self.assertTrue((manager.cache/current['url']).exists())
        manager.verify_current()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--inside',action='store_true');args=parser.parse_args()
    if os.geteuid()!=0:raise SystemExit('root Linux required; no skip-as-proof')
    if not args.inside:
        with tempfile.TemporaryDirectory(prefix='spot-cache-nix-',dir='/run') as tmp:
            folder=Path(tmp)
            for name in [Path(__file__).name,'spot-profile-cache.py','spot_cache.py']:shutil.copyfile(HERE/name,folder/name)
            environment={'PATH':os.environ['PATH'],'HOME':'/root','PYTHONWARNINGS':'error::ResourceWarning','PYTHONDONTWRITEBYTECODE':'1'}
            result=subprocess.run(['unshare','--mount','--pid','--fork','--mount-proc','--net',sys.executable,
                                   str(folder/Path(__file__).name),'--inside'],env=environment,cwd='/run')
            raise SystemExit(result.returncode)
    subprocess.run(['mount','--make-rprivate','/'],check=True)
    for path in ['/home','/root','/tmp']:
        subprocess.run(['mount','-t','tmpfs','-o','mode=0700,size=128M','tmpfs',path],check=True)
    # Per-namespace bind only; no block-device readonly change or global remount.
    subprocess.run(['mount','--bind','/nix','/nix'],check=True)
    subprocess.run(['mount','-o','remount,bind,ro','/nix'],check=True)
    Path('/home/persist').mkdir()
    if ctypes.CDLL(None,use_errno=True).prctl(38,1,0,0,0)!=0:raise RuntimeError('NoNewPrivileges failed')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NativeCacheTests))
    print(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
                      'skipped':len(result.skipped),'private_Nix_stores_only':True,'production_rollout':False,'OS_boot_verified':False}))
    raise SystemExit(0 if result.wasSuccessful() and not result.skipped and result.testsRun==9 else 1)


if __name__=='__main__':main()
