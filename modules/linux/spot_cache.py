#!/usr/bin/env python3
"""Root-private, signed Nix-cache inventory, repair and conservative retention.

All callers serialize with the existing shutdown/cache lock. No network, profile
activation, user-generation deletion, disk GC or secret-key printing occurs here.
Only objects attested by verified inventories can be pruned; unknown files and
objects referenced by ANY remaining narinfo are preserved.
"""
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time
import uuid

OWNER = 0
ALPHABET = '0123456789abcdfghijklmnpqrsvwxyz'
STORE = re.compile(r'/nix/store/[0-9a-df-np-sv-z]{32}-[A-Za-z0-9+._?=-]+\Z')
ID = re.compile(r'[0-9a-f]{32}\Z')
NAR = re.compile(r'nar/([0-9a-df-np-sv-z]{52})\.nar(?:\.(zst|xz|bz2))?\Z')


class Unsafe(RuntimeError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def nix32(raw):
    result = ''
    for n in range((len(raw) * 8 - 1) // 5, -1, -1):
        b = n * 5; i = b // 8
        value = raw[i] >> (b % 8)
        if i + 1 < len(raw):
            value |= raw[i + 1] << (8 - b % 8)
        result += ALPHABET[value & 31]
    return result


def nar_hash(value):
    if isinstance(value,str) and re.fullmatch(r'sha256:[0-9a-df-np-sv-z]{52}',value): return value
    if isinstance(value,str) and value.startswith('sha256-'):
        raw = base64.b64decode(value[7:],validate=True)
        if len(raw)==32: return 'sha256:'+nix32(raw)
    raise Unsafe('source NAR hash unknown')


def store_path(path):
    if not isinstance(path, str) or not STORE.fullmatch(path):
        raise Unsafe('invalid cached store path')
    return path


def trusted(path, limit=1048576):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != OWNER or info.st_mode & 0o022
                or info.st_size > limit):
            raise Unsafe('untrusted cache metadata')
        return stream.read().decode('ascii')


def directory(path, private=False):
    path = Path(path); path.mkdir(parents=True, exist_ok=True, mode=0o700 if private else 0o755)
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != OWNER
            or info.st_mode & (0o077 if private else 0o022)):
        raise Unsafe('untrusted cache directory')
    return path


def publish(path, value):
    path = Path(path); tmp = path.parent / ('.pending-' + uuid.uuid4().hex)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())
        os.replace(tmp, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        tmp.unlink(missing_ok=True)


def file_hash(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != OWNER or info.st_mode & 0o022:
            raise Unsafe('untrusted NAR file')
        h = hashlib.sha256()
        while data := stream.read(1024 * 1024):
            h.update(data)
        after = os.fstat(stream.fileno())
        if (info.st_size, info.st_mtime_ns, info.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise Unsafe('NAR changed during verification')
        return 'sha256:' + nix32(h.digest()), info.st_size


def parse(text, path=None):
    fields = {}; signatures = []
    for line in text.splitlines():
        key, separator, value = line.partition(':')
        if not separator or not value.startswith(' ') or '\x00' in line or '\r' in line:
            raise Unsafe('malformed narinfo')
        value = value[1:]
        if key == 'Sig': signatures.append(value); continue
        if key in fields or key not in {'StorePath','URL','Compression','FileHash','FileSize','NarHash','NarSize','References','Deriver','System','CA'}:
            raise Unsafe('unknown or repeated narinfo field')
        fields[key] = value
    required = {'StorePath','URL','Compression','FileHash','FileSize','NarHash','NarSize','References'}
    if not required <= fields.keys(): raise Unsafe('incomplete narinfo')
    store_path(fields['StorePath'])
    if path is not None and fields['StorePath'] != path: raise Unsafe('narinfo store identity changed')
    match = NAR.fullmatch(fields['URL'])
    if (not match or fields['FileHash'] != 'sha256:' + match[1]
            or fields['Compression'] != {None:'none','zst':'zstd','xz':'xz','bz2':'bzip2'}[match[2]]
            or not re.fullmatch(r'sha256:[0-9a-df-np-sv-z]{52}',fields['NarHash'])):
        raise Unsafe('narinfo object/hash/compression identity unknown')
    for key in ['FileSize','NarSize']:
        if not re.fullmatch(r'0|[1-9][0-9]*',fields[key]): raise Unsafe('invalid NAR size')
        fields[key] = int(fields[key])
    references = ['/nix/store/' + x for x in fields['References'].split()]
    for ref in references: store_path(ref)
    if len(set(references)) != len(references): raise Unsafe('duplicate NAR references')
    fields['references'] = sorted(references)
    fields['signatures'] = signatures
    return fields


def verify_signature(info, key, openssl='openssl'):
    name, encoded = key.split(':', 1)
    public = base64.b64decode(encoded, validate=True)
    if len(public) != 32: raise Unsafe('cache public key unknown')
    message = ('1;' + info['StorePath'] + ';' + info['NarHash'] + ';' + str(info['NarSize'])
               + ';' + ','.join(info['references'])).encode()
    signatures = [s[len(name)+1:] for s in info['signatures'] if s.startswith(name + ':')]
    with tempfile.TemporaryDirectory(prefix='spot-cache-signature-') as tmp:
        root = Path(tmp); (root/'key').write_bytes(bytes.fromhex('302a300506032b6570032100') + public)
        (root/'message').write_bytes(message)
        for signature in signatures:
            try: raw = base64.b64decode(signature, validate=True)
            except ValueError: continue
            if len(raw) != 64: continue
            (root/'signature').write_bytes(raw)
            result = subprocess.run([openssl,'pkeyutl','-verify','-pubin','-keyform','DER','-inkey',str(root/'key'),
                                     '-rawin','-in',str(root/'message'),'-sigfile',str(root/'signature')],
                                    capture_output=True, timeout=10)
            if result.returncode == 0: return
    raise Unsafe('configured cache signature is invalid or absent')


def sync_directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(fd)
    finally:os.close(fd)


def payload(entry):
    info=parse(entry['narinfo'])
    # Compression and extra signatures do not change the signed NAR contents.
    return (info['StorePath'],info['NarHash'],info['NarSize'],tuple(info['references']))


class Cache:
    def __init__(self, config, key, run, current_roots):
        self.config, self.key, self.run, self.current_roots = config, key, run, current_roots
        self.cache = directory(config['cache'], private=True)
        directory(self.cache/'nar')
        self.meta = directory(self.cache/'.spot-cache', private=True)
        self.inventories = directory(self.meta/'inventories', private=True)
        self.quarantine = directory(self.meta/'repair', private=True)
        self.manifest = Path(config['manifest'])

    def current(self):
        try: value = json.loads(trusted(self.manifest))
        except FileNotFoundError: return None
        if not isinstance(value,dict): raise Unsafe('cache manifest unknown')
        return value

    def load(self, ident):
        if not isinstance(ident,str) or not ID.fullmatch(ident): raise Unsafe('inventory identity unknown')
        value = json.loads(trusted(self.inventories/(ident+'.json'), limit=32*1024*1024))
        body = value.get('inventory') if isinstance(value,dict) else None
        if (not isinstance(body,dict) or value.get('sha256') != digest(body) or body.get('schema') != 2
                or body.get('id') != ident or body.get('key') != self.key
                or type(body.get('created_at')) not in (int,float) or not math.isfinite(body['created_at'])
                or not isinstance(body.get('entries'),dict) or not isinstance(body.get('roots'),list)):
            raise Unsafe('cache inventory corrupt or foreign')
        for path, entry in body['entries'].items():
            store_path(path)
            if not isinstance(entry,dict) or not isinstance(entry.get('narinfo'),str): raise Unsafe('cache inventory entry unknown')
            info = parse(entry['narinfo'], path)
            if (entry.get('url'), entry.get('file_hash'), entry.get('file_size')) != (info['URL'], info['FileHash'], info['FileSize']):
                raise Unsafe('inventory object identity contradicts signed metadata')
        return body

    def previous(self):
        m = self.current()
        if m and m.get('schema') == 2:
            ident = m.get('inventory') if m.get('state') == 'verified' else m.get('last_inventory')
            expected = m.get('inventory_sha256') if m.get('state') == 'verified' else m.get('last_inventory_sha256')
            if ident is not None:
                body = self.load(ident)
                if digest(body) != expected: raise Unsafe('cache inventory anchor changed')
                return body
        return None

    def info_path(self, path):
        return self.cache / (Path(store_path(path)).name.split('-',1)[0] + '.narinfo')

    def entry(self, path, contents=True):
        text = trusted(self.info_path(path)); info = parse(text,path)
        verify_signature(info, self.key, self.config.get('openssl','openssl'))
        directory(self.cache/'nar')
        file = self.cache/info['URL']
        if contents:
            h, size = file_hash(file)
            if h != info['FileHash'] or size != info['FileSize']: raise Unsafe('cached NAR file damaged or truncated')
        else:
            s = file.lstat()
            if not stat.S_ISREG(s.st_mode) or s.st_uid != OWNER or s.st_mode & 0o022 or s.st_size != info['FileSize']:
                raise Unsafe('cached NAR file absent or identity unknown')
        return {'narinfo':text,'url':info['URL'],'file_hash':info['FileHash'],'file_size':info['FileSize']}

    def verify_entries(self, entries, contents=True):
        for path, expected in entries.items():
            actual = self.entry(path, contents=contents)
            if actual != expected: raise Unsafe('published cache metadata changed')
        if contents and entries:
            # Independent Nix decoding/NAR-hash verification, without network or
            # accepting a mere signature-name prefix/content-addressed shortcut.
            with tempfile.TemporaryDirectory(prefix='spot-cache-nix-client-') as tmp:
                old = os.environ.get('XDG_CACHE_HOME'); os.environ['XDG_CACHE_HOME'] = tmp
                try:
                    self.run('nix','--extra-experimental-features','nix-command','--option','trusted-public-keys',self.key,'--option','substituters','',
                             '--option','narinfo-cache-positive-ttl','0','--option','narinfo-cache-negative-ttl','0',
                             'store','verify','--store','file://'+str(self.cache),'--sigs-needed','1',*sorted(entries))
                finally:
                    if old is None: os.environ.pop('XDG_CACHE_HOME',None)
                    else: os.environ['XDG_CACHE_HOME'] = old

    def verify_current(self, contents=True):
        m = self.current()
        if not m or m.get('schema') != 2 or m.get('state') != 'verified': raise Unsafe('cache checkpoint is not verified')
        body = self.previous()
        if self.current_roots() != (m.get('user_profile'),m.get('roots')) or body['roots'] != m['roots']:
            raise Unsafe('profile generations changed after checkpoint')
        self.verify_entries(body['entries'],contents=contents)
        if self.current() != m or self.current_roots() != (m['user_profile'],m['roots']):
            raise Unsafe('cache verification raced profile/manifest change')
        return body

    def invalidate(self):
        # Never retain a matching "good" readiness marker after detecting bad
        # bytes in an unchanged profile. This is NOT a new completed export.
        previous = self.previous()
        value = {'schema':2,'state':'unverified','reason':'cache_refresh_or_verification_incomplete','cache_public_key':self.key}
        if previous:
            value.update(last_inventory=previous['id'],last_inventory_sha256=digest(previous))
        publish(self.manifest,value)

    def repair(self, paths, expected=None):
        previous = self.previous()
        known = previous['entries'] if previous else {}
        bad = []
        for path in paths:
            try:
                entry = self.entry(path); info = parse(entry['narinfo'],path)
                if expected is not None and (info['NarSize'] != expected[path]['narSize']
                        or info['NarHash'] != nar_hash(expected[path]['narHash'])):
                    raise Unsafe('cache differs from source store contents')
            except (OSError,ValueError,Unsafe): bad.append(path)
        if not bad: return 0
        self.invalidate()
        ident = uuid.uuid4().hex; target = self.quarantine/ident
        moves = []
        for path in bad:
            info_file = self.info_path(path)
            try: text = trusted(info_file); info = parse(text,path); verify_signature(info,self.key,self.config.get('openssl','openssl'))
            except (OSError,ValueError,Unsafe):
                info = parse(known[path]['narinfo'],path) if path in known else None
            candidates = [info_file]
            if info:
                body = self.cache/info['URL']
                try: damaged = file_hash(body) != (info['FileHash'], info['FileSize'])
                except FileNotFoundError: damaged = False
                if damaged: candidates.append(body)
            for file in candidates:
                if not file.exists() and not file.is_symlink(): continue
                s = file.lstat()
                if not stat.S_ISREG(s.st_mode) or s.st_uid != OWNER or s.st_mode & 0o022 or s.st_nlink != 1:
                    raise Unsafe('repair will not move an untrusted cache object')
                relative = str(file.relative_to(self.cache))
                if relative in [x['source'] for x in moves]: continue
                h,size = file_hash(file)
                moves.append({'source':relative,'target':str(len(moves)),'hash':h,'size':size})
        if not moves:return len(bad)  # ordinary missing exports have no old bytes to quarantine
        directory(target,private=True)
        publish(target/'intent.json', {'schema':1,'paths':bad,'moves':moves})
        for move in moves:
            src = self.cache/move['source']
            if file_hash(src) != (move['hash'],move['size']): raise Unsafe('repair source changed')
            os.rename(src,target/move['target'])
        for folder in {target,self.cache,self.cache/'nar'}:sync_directory(folder)
        return len(bad)

    def save_inventory(self, entries, roots, parent=None, kind='checkpoint'):
        ident = uuid.uuid4().hex
        body = {'schema':2,'id':ident,'kind':kind,'created_at':time.time(),'key':self.key,
                'roots':roots,'parent':parent,'entries':entries}
        publish(self.inventories/(ident+'.json'),{'inventory':body,'sha256':digest(body)})
        return body

    def adopt(self):
        if any(ID.fullmatch(p.stem) and p.suffix=='.json' for p in self.inventories.iterdir()): return None
        entries = {}
        for file in self.cache.glob('*.narinfo'):
            text = trusted(file)
            if not any(s.startswith('Sig: '+self.key.split(':',1)[0]+':') for s in text.splitlines()): continue
            try:
                info = parse(text)
                if file != self.info_path(info['StorePath']): continue
                entries[info['StorePath']] = self.entry(info['StorePath'])
            except (OSError,ValueError,Unsafe):
                continue  # unverifiable legacy bytes are preserved, NOT adopted as garbage
        self.verify_entries(entries)
        return self.save_inventory(entries,[],kind='adopted') if entries else None

    def checkpoint(self, profile, paths, rows, parent=None):
        entries = {row['path']:self.entry(row['path']) for row in rows}
        if len(entries) != len(rows) or not set(paths) <= entries.keys(): raise Unsafe('incomplete closure inventory')
        by_path = {row['path']:row for row in rows}
        for path,entry in entries.items():
            info = parse(entry['narinfo'],path)
            if not set(info['references']) <= entries.keys(): raise Unsafe('closure inventory misses a reference')
            if info['NarSize'] != by_path[path]['narSize'] or info['NarHash'] != nar_hash(by_path[path]['narHash']):
                raise Unsafe('published cache does not match source store contents')
        self.verify_entries(entries)
        if self.current_roots() != (profile,paths): raise Unsafe('profile generations changed during export')
        body = self.save_inventory(entries,paths,parent=parent)
        manifest = {'schema':2,'state':'verified','exported_at':time.time(),'system':os.path.realpath(self.config.get('system_profile','/run/current-system')),
                    'user_profile':profile,'roots':paths,'cached_paths':len(rows),'cache_public_key':self.key,
                    'inventory':body['id'],'inventory_sha256':digest(body)}
        publish(self.manifest,manifest)
        return body

    def retention_plan(self):
        current=self.previous()
        keep=self.config.get('keep_checkpoints',2);grace=self.config.get('prune_grace_seconds',86400)
        if type(keep) is not int or keep<2 or type(grace) is not int or grace<0:raise Unsafe('unsafe cache retention policy')
        retained={};ids=set();cursor=current
        for _ in range(keep):
            if cursor is None or cursor.get('kind')=='adopted':break
            if cursor['id'] in ids:raise Unsafe('inventory parent cycle')
            ids.add(cursor['id'])
            for path,entry in cursor['entries'].items():
                if path in retained and payload(retained[path])!=payload(entry):
                    raise Unsafe('retained cache payloads disagree; cleanup deferred')
                retained.setdefault(path,entry)  # latest metadata; extra signatures are not a different NAR
            cursor=self.load(cursor['parent']) if cursor.get('parent') is not None else None
        protected=set(retained);urls={e['url'] for e in retained.values()};eligible=[]
        for file in self.inventories.iterdir():
            if file.name.startswith('.pending-'):continue  # preserve uncertain crash artifacts
            if file.suffix!='.json' or not ID.fullmatch(file.stem):raise Unsafe('unknown inventory artifact; cleanup deferred')
            old=self.load(file.stem)
            if old['id'] in ids or time.time()-old['created_at']<grace:
                protected.update(old['entries']);urls.update(e['url'] for e in old['entries'].values())
            else:eligible.extend(old['entries'].items())
        return retained,protected,urls,eligible

    def garbage_pending(self):
        if self.previous() is None:return False
        _,protected,protected_urls,eligible=self.retention_plan()
        referenced={parse(trusted(file))['URL'] for file in self.cache.glob('*.narinfo')}
        for path,entry in eligible:
            file=self.info_path(path)
            if path not in protected and file.exists() and trusted(file)==entry['narinfo']:return True
            if entry['url'] not in protected_urls|referenced and (self.cache/entry['url']).exists():return True
        return False

    def prune(self):
        anchor=self.current();self.verify_current(contents=False)
        retained,protected,protected_urls,eligible=self.retention_plan()
        self.verify_entries(retained)  # BOTH retained checkpoints, not just a latest ACK.
        candidates={}
        for path,entry in eligible:
            if path not in protected:candidates.setdefault(path,[]).append(entry)
        removed=0
        for path,versions in candidates.items():
            file=self.info_path(path)
            if not file.exists():continue
            self._anchor(anchor)
            if self.entry(path) not in versions:continue  # changed/foreign replacement is NOT owned garbage
            if file.lstat().st_nlink!=1:raise Unsafe('linked narinfo is not deletable')
            file.unlink();removed+=1
        # URL protection is separate from store-path protection: recompressing
        # the same store path must not leak every historical compressed body.
        referenced={parse(trusted(file))['URL'] for file in self.cache.glob('*.narinfo')}
        urls={entry['url']:(entry['file_hash'],entry['file_size']) for _,entry in eligible}
        bodies=0
        for url,identity in urls.items():
            if url in referenced|protected_urls:continue
            if not NAR.fullmatch(url):raise Unsafe('unknown garbage object name')
            file=self.cache/url
            if not file.exists():continue
            self._anchor(anchor)
            if file_hash(file)!=identity:continue
            if file.lstat().st_nlink!=1:raise Unsafe('linked NAR is not deletable')
            file.unlink();bodies+=1
        for folder in [self.cache,self.cache/'nar']:sync_directory(folder)
        self._anchor(anchor);self.verify_current()
        return {'narinfos_removed':removed,'nar_objects_removed':bodies}

    def cleanup_repairs(self):
        if not any(self.quarantine.iterdir()): return 0
        anchor = self.current(); inventory = self.verify_current(); removed = 0
        for folder in self.quarantine.iterdir():
            if not ID.fullmatch(folder.name): raise Unsafe('unknown repair artifact')
            directory(folder,private=True)
            if not any(folder.iterdir()):
                self._anchor(anchor);folder.rmdir();sync_directory(self.quarantine)
                continue  # death after removing the intent but before removing its EMPTY directory
            intent = json.loads(trusted(folder/'intent.json'))
            if (not isinstance(intent,dict) or intent.get('schema') != 1
                    or not isinstance(intent.get('paths'),list) or not isinstance(intent.get('moves'),list)):
                raise Unsafe('unknown repair intent')
            for path in intent['paths']: store_path(path)
            if not set(intent['paths']) <= inventory['entries'].keys(): continue
            names = {str(i) for i in range(len(intent['moves']))} | {'intent.json'}
            if not {p.name for p in folder.iterdir()} <= names: raise Unsafe('unowned repair file')
            for index,move in enumerate(intent['moves']):
                if not isinstance(move,dict) or move.get('target') != str(index): raise Unsafe('repair target changed')
                file = folder/str(index)
                if not file.exists(): continue
                self._anchor(anchor)
                if file_hash(file) != (move.get('hash'),move.get('size')) or file.lstat().st_nlink != 1:
                    raise Unsafe('repair evidence changed; preserve it')
                file.unlink(); removed += 1
            self._anchor(anchor)
            sync_directory(folder)
            (folder/'intent.json').unlink();sync_directory(folder)
            folder.rmdir();sync_directory(self.quarantine)
        return removed

    def _anchor(self, manifest):
        if self.current() != manifest or self.current_roots() != (manifest['user_profile'],manifest['roots']):
            raise Unsafe('cache retention anchor/profile changed')
