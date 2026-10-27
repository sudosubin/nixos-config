"""Offline cache policy/filesystem tests; crypto/Nix subprocesses are mocked.
Actual Ed25519, compression, isolated stores and GC are tested separately on Linux.
"""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import spot_cache as cache

spec=importlib.util.spec_from_file_location('profile_cache',Path(__file__).with_name('spot-profile-cache.py'))
profile_cache=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile_cache)
SYSTEM='/nix/store/'+('a'*32)+'-system'
PROFILE='/nix/store/'+('b'*32)+'-profile'
OLD='/nix/store/'+('c'*32)+'-old-profile'
REF='/nix/store/'+('d'*32)+'-reference'
KEY='fixture:'+base64.b64encode(bytes(32)).decode()
SIG=base64.b64encode(bytes(64)).decode()


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.location=self.root/'cache';self.location.mkdir(mode=0o700)
        self.owner=patch.object(cache,'OWNER',os.geteuid());self.owner.start();self.addCleanup(self.owner.stop)
        signer=patch.object(cache,'verify_signature');self.signature=signer.start();self.addCleanup(signer.stop)
        self.paths=sorted([SYSTEM,PROFILE]);self.profile=PROFILE
        system=self.root/'system';system.symlink_to(SYSTEM)
        self.config={'cache':str(self.location),'manifest':str(self.root/'manifest.json'),
                     'system_profile':str(system),'keep_checkpoints':2,'prune_grace_seconds':0}
        self.run=Mock(return_value='')
        self.manager=cache.Cache(self.config,KEY,self.run,lambda:(self.profile,self.paths.copy()))
        self.add(SYSTEM,b'system');self.add(PROFILE,b'profile')

    def add(self,path,data=b'fixture',refs=()):
        directory=self.location/'nar';directory.mkdir(exist_ok=True,mode=0o700)
        filehash='sha256:'+cache.nix32(hashlib.sha256(data).digest());url='nar/'+filehash[7:]+'.nar.zst'
        (self.location/url).write_bytes(data)
        text='\n'.join(['StorePath: '+path,'URL: '+url,'Compression: zstd','FileHash: '+filehash,
                        'FileSize: '+str(len(data)),'NarHash: '+filehash,'NarSize: '+str(len(data)),
                        'References: '+' '.join(Path(p).name for p in refs),'Sig: fixture:'+SIG])+'\n'
        self.manager.info_path(path).write_text(text)
        return self.manager.entry(path)

    def rows(self):
        return [{'path':p,'narSize':cache.parse(cache.trusted(self.manager.info_path(p)))['NarSize'],
                 'narHash':cache.parse(cache.trusted(self.manager.info_path(p)))['NarHash']} for p in self.paths]

    def checkpoint(self,parent=None):
        return self.manager.checkpoint(self.profile,self.paths.copy(),self.rows(),parent=parent['id'] if parent else None)

    def obsolete(self,data=b'old-profile'):
        self.add(OLD,data);self.paths=sorted([SYSTEM,PROFILE,OLD]);first=self.checkpoint()
        self.paths=sorted([SYSTEM,PROFILE]);second=self.checkpoint(first);third=self.checkpoint(second)
        return first,second,third


class MetadataTests(Fixture):
    def test_nix_base32_zero_and_sri(self):
        self.assertEqual(cache.nix32(bytes(32)),'0'*52)
        self.assertEqual(cache.nar_hash('sha256-'+base64.b64encode(bytes(32)).decode()),'sha256:'+'0'*52)

    def test_unknown_hash_algorithm_rejected(self):
        with self.assertRaises(cache.Unsafe):cache.nar_hash('sha1:bad')

    def test_unsafe_url_and_wrong_compression_rejected(self):
        text=cache.trusted(self.manager.info_path(PROFILE));url=cache.parse(text)['URL']
        for changed in [text.replace(url,'../secret'),text.replace('Compression: zstd','Compression: none')]:
            with self.subTest(changed=changed),self.assertRaises(cache.Unsafe):cache.parse(changed)

    def test_wrong_store_identity(self):
        with self.assertRaises(cache.Unsafe):cache.parse(cache.trusted(self.manager.info_path(PROFILE)),OLD)

    def test_duplicate_and_unknown_fields_rejected(self):
        text=cache.trusted(self.manager.info_path(PROFILE))
        for addition in ['StorePath: '+PROFILE+'\n','FutureAsync: unknown\n']:
            with self.subTest(addition=addition),self.assertRaises(cache.Unsafe):cache.parse(text+addition)

    def test_malformed_size_or_missing_field(self):
        text=cache.trusted(self.manager.info_path(PROFILE))
        for changed in [text.replace('NarSize: 7','NarSize: -1'),text.replace('References: \n','')]:
            with self.subTest(changed=changed),self.assertRaises(cache.Unsafe):cache.parse(changed)

    def test_duplicate_references_rejected(self):
        text=cache.trusted(self.manager.info_path(PROFILE)).replace('References: ','References: '+Path(OLD).name+' '+Path(OLD).name)
        with self.assertRaises(cache.Unsafe):cache.parse(text)

    def test_same_size_body_damage_detected(self):
        entry=self.manager.entry(PROFILE);(self.location/entry['url']).write_bytes(b'corrupt')
        with self.assertRaises(cache.Unsafe):self.manager.entry(PROFILE)

    def test_body_symlink_rejected(self):
        entry=self.manager.entry(PROFILE);p=self.location/entry['url'];p.unlink();p.symlink_to(self.root/'missing')
        with self.assertRaises(OSError):self.manager.entry(PROFILE)

    def test_metadata_symlink_rejected(self):
        p=self.manager.info_path(PROFILE);p.unlink();p.symlink_to(self.root/'missing')
        with self.assertRaises(OSError):self.manager.entry(PROFILE)

    def test_wrong_owner_is_untrusted(self):
        with patch.object(cache.os,'fstat',return_value=SimpleNamespace(st_mode=0o100600,st_uid=-1,st_size=1)):
            with self.assertRaises(cache.Unsafe):cache.trusted(self.manager.info_path(PROFILE))


class SignatureTests(unittest.TestCase):
    def info(self):
        return {'StorePath':PROFILE,'NarHash':'sha256:'+'0'*52,'NarSize':1,'references':[OLD],
                'signatures':['fixture:'+SIG]}

    def test_same_signer_name_is_not_a_signature_proof(self):
        with patch.object(cache.subprocess,'run',return_value=SimpleNamespace(returncode=1)) as run:
            with self.assertRaises(cache.Unsafe):cache.verify_signature(self.info(),KEY)
            run.assert_called_once()

    def test_absent_or_truncated_signature_never_invokes_crypto_success(self):
        for value in ['other:'+SIG,'fixture:c2hvcnQ=']:
            info=self.info();info['signatures']=[value]
            with self.subTest(value=value),patch.object(cache.subprocess,'run') as run:
                with self.assertRaises(cache.Unsafe):cache.verify_signature(info,KEY)
                run.assert_not_called()

    def test_actual_message_and_ed25519_public_key_frame(self):
        def verify(argv,**kwargs):
            key=Path(argv[argv.index('-inkey')+1]).read_bytes()
            message=Path(argv[argv.index('-in')+1]).read_bytes()
            self.assertEqual(key,bytes.fromhex('302a300506032b6570032100')+bytes(32))
            self.assertEqual(message,('1;'+PROFILE+';sha256:'+'0'*52+';1;'+OLD).encode())
            self.assertIn('-rawin',argv);self.assertIn('-pubin',argv)
            return SimpleNamespace(returncode=0)
        with patch.object(cache.subprocess,'run',side_effect=verify):cache.verify_signature(self.info(),KEY)


class CheckpointTests(Fixture):
    def test_checkpoint_has_verified_content_anchor(self):
        body=self.checkpoint();self.assertEqual(self.manager.verify_current(),body)
        self.assertEqual(self.manager.current()['inventory_sha256'],cache.digest(body))
        args=self.run.call_args.args
        self.assertIn('verify',args);self.assertIn('--sigs-needed',args);self.assertNotIn('--no-contents',args)
        self.assertEqual(args[args.index('substituters')+1],'')

    def test_incomplete_closure_cannot_publish(self):
        with self.assertRaises(cache.Unsafe):self.manager.checkpoint(PROFILE,self.paths,self.rows()[:1])
        self.assertIsNone(self.manager.current())

    def test_missing_reference_cannot_publish(self):
        self.add(PROFILE,b'profile',refs=[REF])
        with self.assertRaises(cache.Unsafe):self.checkpoint()
        self.assertIsNone(self.manager.current())

    def test_source_nar_hash_must_match_cache(self):
        rows=self.rows();rows[0]['narHash']='sha256:'+'0'*52
        with self.assertRaises(cache.Unsafe):self.manager.checkpoint(PROFILE,self.paths,rows)
        self.assertIsNone(self.manager.current())

    def test_profile_change_during_checkpoint_cannot_publish(self):
        rows=self.rows();paths=self.paths.copy();self.paths.append(OLD)
        with self.assertRaises(cache.Unsafe):self.manager.checkpoint(PROFILE,paths,rows)
        self.assertIsNone(self.manager.current())

    def test_legacy_marker_is_not_completed_inventory_proof(self):
        cache.publish(self.manager.manifest,{'schema':1,'user_profile':PROFILE,'roots':self.paths})
        with self.assertRaises(cache.Unsafe):self.manager.verify_current()

    def test_corrupt_inventory_hash_rejected(self):
        body=self.checkpoint();p=self.manager.inventories/(body['id']+'.json');v=json.loads(p.read_text())
        v['inventory']['roots']=[];p.write_text(json.dumps(v))
        with self.assertRaises(cache.Unsafe):self.manager.verify_current()

    def test_changed_inventory_anchor_rejected(self):
        self.checkpoint();m=self.manager.current();m['inventory_sha256']='0'*64;cache.publish(self.manager.manifest,m)
        with self.assertRaises(cache.Unsafe):self.manager.verify_current()

    def test_unverified_marker_preserves_only_repair_parent_not_readiness(self):
        body=self.checkpoint();self.manager.invalidate()
        self.assertEqual(self.manager.previous(),body)
        with self.assertRaises(cache.Unsafe):self.manager.verify_current()

    def test_profile_change_during_final_readback_rejected(self):
        self.checkpoint()
        with patch.object(self.manager,'current_roots',side_effect=[(PROFILE,self.paths),(PROFILE,self.paths+[OLD])]):
            with self.assertRaises(cache.Unsafe):self.manager.verify_current()

    def test_quick_metadata_is_not_payload_integrity_authority(self):
        self.checkpoint();entry=self.manager.entry(PROFILE);(self.location/entry['url']).write_bytes(b'corrupt')
        self.manager.verify_current(contents=False)
        with self.assertRaises(cache.Unsafe):self.manager.verify_current()


class RetentionTests(Fixture):
    def test_current_and_previous_checkpoint_protect_old_objects(self):
        self.add(OLD,b'old');self.paths=sorted([SYSTEM,PROFILE,OLD]);first=self.checkpoint()
        self.paths=sorted([SYSTEM,PROFILE]);self.checkpoint(first)
        self.assertEqual(self.manager.prune(),{'narinfos_removed':0,'nar_objects_removed':0})
        self.assertTrue(self.manager.info_path(OLD).exists())

    def test_only_attested_unreferenced_objects_are_deleted(self):
        self.obsolete();unknown=self.location/'unowned-note';unknown.write_text('preserve')
        result=self.manager.prune();self.assertEqual(result['narinfos_removed'],1)
        self.assertEqual(result['nar_objects_removed'],1);self.assertTrue(unknown.exists())
        self.manager.verify_current()

    def test_shared_nar_survives_other_store_path_retirement(self):
        self.obsolete(data=b'profile');entry=self.manager.entry(PROFILE)
        result=self.manager.prune();self.assertEqual(result['narinfos_removed'],1)
        self.assertEqual(result['nar_objects_removed'],0);self.assertTrue((self.location/entry['url']).exists())

    def test_any_remaining_narinfo_protects_shared_body(self):
        self.obsolete();old=cache.parse(cache.trusted(self.manager.info_path(OLD)))
        text=cache.trusted(self.manager.info_path(OLD)).replace(OLD,REF).replace('Sig: fixture:','Sig: foreign:')
        self.manager.info_path(REF).write_text(text)
        self.manager.prune();self.assertTrue((self.location/old['URL']).exists())
        self.assertTrue(self.manager.info_path(REF).exists())

    def test_latest_corruption_blocks_cleanup(self):
        self.obsolete();entry=self.manager.entry(PROFILE);(self.location/entry['url']).write_bytes(b'corrupt')
        with self.assertRaises(cache.Unsafe):self.manager.prune()
        self.assertTrue(self.manager.info_path(OLD).exists())

    def test_previous_checkpoint_corruption_blocks_cleanup(self):
        self.add(OLD,b'old');self.add(REF,b'reference')
        self.paths=sorted([SYSTEM,PROFILE,OLD]);first=self.checkpoint()
        self.paths=sorted([SYSTEM,PROFILE,REF]);second=self.checkpoint(first)
        self.paths=sorted([SYSTEM,PROFILE]);self.checkpoint(second)
        entry=self.manager.entry(REF);(self.location/entry['url']).write_bytes(b'broken---')
        with self.assertRaises(cache.Unsafe):self.manager.prune()
        self.assertTrue(self.manager.info_path(OLD).exists())

    def test_grace_and_invalid_retention_policy(self):
        self.obsolete();self.config['prune_grace_seconds']=86400
        self.assertFalse(self.manager.garbage_pending());self.assertEqual(self.manager.prune()['narinfos_removed'],0)
        for values in [(1,0),(2,-1),(True,0)]:
            self.config['keep_checkpoints'],self.config['prune_grace_seconds']=values
            with self.subTest(values=values),self.assertRaises(cache.Unsafe):self.manager.prune()

    def test_manifest_change_blocks_before_deletion(self):
        self.obsolete()
        with patch.object(self.manager,'_anchor',side_effect=cache.Unsafe('superseded')):
            with self.assertRaises(cache.Unsafe):self.manager.prune()
        self.assertTrue(self.manager.info_path(OLD).exists())

    def test_interrupted_metadata_cleanup_reconciles_orphan_body(self):
        self.obsolete();entry=self.manager.entry(OLD);self.manager.info_path(OLD).unlink()
        self.assertTrue(self.manager.garbage_pending());self.manager.prune()
        self.assertFalse((self.location/entry['url']).exists())

    def test_historical_body_version_of_retained_store_path_is_not_leaked(self):
        first=self.checkpoint();old=self.manager.entry(PROFILE)
        self.add(PROFILE,b'new-version');second=self.checkpoint(first);self.checkpoint(second)
        self.assertTrue(self.manager.garbage_pending())
        out=self.manager.prune();self.assertEqual(out['narinfos_removed'],0);self.assertEqual(out['nar_objects_removed'],1)
        self.assertFalse((self.location/old['url']).exists());self.manager.verify_current()

    def test_recent_reuse_protects_object_even_when_an_older_inventory_is_eligible(self):
        self.add(OLD,b'old');self.paths=sorted([SYSTEM,PROFILE,OLD]);first=self.checkpoint();second=self.checkpoint(first)
        self.paths=sorted([SYSTEM,PROFILE]);third=self.checkpoint(second);self.checkpoint(third)
        first['created_at']-=172800
        cache.publish(self.manager.inventories/(first['id']+'.json'),{'inventory':first,'sha256':cache.digest(first)})
        self.config['prune_grace_seconds']=86400
        self.assertFalse(self.manager.garbage_pending());self.assertEqual(self.manager.prune()['narinfos_removed'],0)
        self.assertTrue(self.manager.info_path(OLD).exists())

    def test_legacy_adoption_is_ownership_not_an_eternal_profile_checkpoint(self):
        self.add(OLD,b'legacy-orphan');baseline=self.manager.adopt();self.checkpoint(baseline)
        self.assertTrue(self.manager.garbage_pending());out=self.manager.prune()
        self.assertEqual(out['narinfos_removed'],1);self.assertEqual(out['nar_objects_removed'],1)
        self.manager.verify_current()

    def test_unknown_inventory_artifact_defers_cleanup(self):
        self.obsolete();(self.manager.inventories/'unowned.json').write_text('{}')
        with self.assertRaises(cache.Unsafe):self.manager.prune()
        self.assertTrue(self.manager.info_path(OLD).exists())

    def test_unknown_remaining_metadata_defers_body_deletion(self):
        self.obsolete();entry=self.manager.entry(OLD)
        (self.location/('0'*32+'.narinfo')).write_text('Unknown: state\n')
        with self.assertRaises(cache.Unsafe):self.manager.prune()
        self.assertTrue((self.location/entry['url']).exists())


class RepairTests(Fixture):
    def test_corruption_is_quarantined_with_durable_intent_before_reexport(self):
        self.checkpoint();entry=self.manager.entry(PROFILE);(self.location/entry['url']).write_bytes(b'corrupt')
        self.assertEqual(self.manager.repair([PROFILE]),1)
        self.assertEqual(self.manager.current()['state'],'unverified')
        folder=next(self.manager.quarantine.iterdir());intent=json.loads((folder/'intent.json').read_text())
        self.assertEqual(len(intent['moves']),2)
        self.assertTrue(any(p.read_bytes()==b'corrupt' for p in folder.iterdir() if p.name!='intent.json'))

    def test_failed_copy_preserves_quarantined_bytes_and_unverified_readiness(self):
        self.checkpoint();entry=self.manager.entry(PROFILE);(self.location/entry['url']).write_bytes(b'corrupt')
        self.manager.repair([PROFILE])
        with self.assertRaises(cache.Unsafe):self.manager.cleanup_repairs()
        self.assertTrue(any(self.manager.quarantine.iterdir()))

    def test_good_body_is_not_moved_for_bad_metadata(self):
        self.checkpoint();entry=self.manager.entry(PROFILE);self.manager.info_path(PROFILE).write_text('bad')
        self.manager.repair([PROFILE]);self.assertTrue((self.location/entry['url']).exists())
        intent=json.loads((next(self.manager.quarantine.iterdir())/'intent.json').read_text())
        self.assertEqual(len(intent['moves']),1)

    def test_verified_repair_cleans_only_exact_owned_evidence(self):
        parent=self.checkpoint();entry=self.manager.entry(PROFILE);(self.location/entry['url']).write_bytes(b'corrupt')
        self.manager.repair([PROFILE]);self.add(PROFILE,b'profile');self.checkpoint(parent)
        self.assertEqual(self.manager.cleanup_repairs(),2);self.assertFalse(any(self.manager.quarantine.iterdir()))

    def test_empty_owned_folder_after_interrupted_intent_removal_is_reconciled(self):
        self.checkpoint();(self.manager.quarantine/('a'*32)).mkdir(mode=0o700)
        self.assertEqual(self.manager.cleanup_repairs(),0);self.assertFalse(any(self.manager.quarantine.iterdir()))

    def test_interrupted_cleanup_with_already_removed_owned_file_can_resume(self):
        parent=self.checkpoint();self.manager.info_path(PROFILE).write_text('bad');self.manager.repair([PROFILE])
        folder=next(self.manager.quarantine.iterdir());(folder/'0').unlink()
        self.add(PROFILE,b'profile');self.checkpoint(parent)
        self.assertEqual(self.manager.cleanup_repairs(),0);self.assertFalse(any(self.manager.quarantine.iterdir()))

    def test_unknown_quarantine_file_is_preserved(self):
        parent=self.checkpoint();self.manager.info_path(PROFILE).write_text('bad');self.manager.repair([PROFILE])
        folder=next(self.manager.quarantine.iterdir());(folder/'unowned').write_text('preserve')
        self.add(PROFILE,b'profile');self.checkpoint(parent)
        with self.assertRaises(cache.Unsafe):self.manager.cleanup_repairs()
        self.assertEqual((folder/'unowned').read_text(),'preserve')


class ProfileGenerationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        for name,path in [('system',SYSTEM),('profile',PROFILE)]: (self.root/name).symlink_to(path)
        self.directory=self.root/'generations';self.directory.mkdir()
        self.config={'system_profile':str(self.root/'system'),'profile':str(self.root/'profile'),
                     'home_profile':str(self.root/'missing'),'uid':os.geteuid(),'generation_directories':[str(self.directory)]}

    def test_all_retained_and_dangling_generation_targets_are_selected(self):
        (self.directory/'profile-1-link').symlink_to(OLD);(self.directory/'home-manager-92-link').symlink_to(REF)
        self.assertEqual(profile_cache.roots(self.config),(PROFILE,sorted([SYSTEM,PROFILE,OLD,REF])))

    def test_named_profiles_and_direct_current_aliases_are_retained(self):
        (self.directory/'named+profile-42-link').symlink_to(OLD)
        (self.directory/'channels').symlink_to(REF)
        self.assertEqual(profile_cache.roots(self.config),(PROFILE,sorted([SYSTEM,PROFILE,OLD,REF])))

    def test_unrelated_files_are_not_interpreted_as_profile_generations(self):
        (self.directory/'unrelated-note').write_text('private text')
        self.assertEqual(profile_cache.roots(self.config),(PROFILE,sorted([SYSTEM,PROFILE])))

    def test_malformed_recognized_generation_blocks_instead_of_skipping(self):
        (self.directory/'profile-1-link').write_text('not a symlink')
        with self.assertRaises(ValueError):profile_cache.roots(self.config)

    def test_non_store_target_rejected(self):
        (self.directory/'profile-1-link').symlink_to('/root/private')
        with self.assertRaises(ValueError):profile_cache.roots(self.config)

    def test_symlink_or_writable_generation_directory_rejected(self):
        self.config['generation_directories']=[str(self.root/'alias')];(self.root/'alias').symlink_to(self.directory)
        with self.assertRaises(ValueError):profile_cache.roots(self.config)
        self.config['generation_directories']=[str(self.directory)];self.directory.chmod(0o777)
        with self.assertRaises(ValueError):profile_cache.roots(self.config)


if __name__=='__main__':unittest.main()
