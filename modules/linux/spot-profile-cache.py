#!/usr/bin/env python3
"""Restore/cache persistent Nix profiles without Git, network caches, or a laptop.

The logical store remains /nix/store. Only NAR data and profile metadata persist
on /home. Never run activation scripts from the cache. A failed export never
publishes a completed checkpoint; a bad matching readiness marker is invalidated.
Share the shutdown guard's lock during all cache I/O.
"""
from __future__ import annotations

import argparse
import base64
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import subprocess

import spot_cache

STORE_PATH = re.compile(r"/nix/store/[0-9a-df-np-sv-z]{32}-[A-Za-z0-9+._?=-]+\Z")


def store_path(value):
    if not isinstance(value, str) or not STORE_PATH.fullmatch(value):
        raise ValueError("invalid store path")
    return value


def trusted_text(path, *, secret=False, limit=65536):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        forbidden = 0o077 if secret else 0o022
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & forbidden or info.st_size > limit:
            raise ValueError("untrusted persistence file")
        return stream.read()


def secure_directory(path, mode):
    path = Path(path)
    path.mkdir(mode=mode, parents=True, exist_ok=True)
    info = path.lstat()
    forbidden = 0o077 if mode == 0o700 else 0o022
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & forbidden:
        raise ValueError("untrusted persistence directory")
    return path


def public_key(path):
    return validated_key(trusted_text(path, limit=4096).strip())


def validated_key(key):
    if not isinstance(key,str) or not re.fullmatch(r"[A-Za-z0-9._-]+:[A-Za-z0-9+/=]+", key):
        raise ValueError("invalid cache public key")
    if len(base64.b64decode(key.split(":", 1)[1], validate=True)) != 32:
        raise ValueError("invalid cache public key length")
    return key


def command(*args, timeout=900):
    return subprocess.check_output(args, text=True, timeout=timeout).strip()


def check_home(config):
    target = command("findmnt", "-n", "-o", "TARGET", "--target", "/home")
    uuid = command("findmnt", "-n", "-o", "UUID", "--target", "/home")
    if target != "/home" or uuid != config["home_uuid"]:
        raise ValueError("persistent home is not mounted")


def roots(config):
    result = [store_path(os.path.realpath(config.get("system_profile", "/run/current-system")))]
    profile = store_path(os.path.realpath(config["profile"]))
    result.append(profile)
    for name in config.get("home_generations", []):
        result.append(store_path(name))
    extra = Path(config["home_profile"])
    if extra.is_symlink() or extra.exists():
        result.append(store_path(os.path.realpath(extra)))
    # Named profiles/channels are profiles too. Do not silently protect only
    # the default profile/home-manager names when other aliases exist here.
    pattern = re.compile(r'[A-Za-z0-9+._?=-]+-[1-9][0-9]*-link\Z')
    for name in config.get('generation_directories', []):
        directory = Path(name)
        if not directory.exists() and not directory.is_symlink():
            continue
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid not in {0,config.get('uid',1001)} or info.st_mode & 0o022:
            raise ValueError('untrusted profile generation directory')
        for entry in directory.iterdir():
            info = entry.lstat()
            if not pattern.fullmatch(entry.name) and not stat.S_ISLNK(info.st_mode):continue
            if not stat.S_ISLNK(info.st_mode) or info.st_uid not in {0,config.get('uid',1001)}:
                raise ValueError('unknown retained profile generation')
            result.append(store_path(os.path.realpath(entry)))
    return profile, sorted(set(result))


def rows_from_json(raw):
    data = json.loads(raw)
    rows = [{"path": p, **value} for p, value in data.items()] if isinstance(data, dict) else data
    if not isinstance(rows, list) or not rows:
        raise ValueError("empty closure")
    for row in rows:
        store_path(row["path"])
        if type(row["narSize"]) is not int or row["narSize"] < 0:
            raise ValueError("invalid NAR size")
    return rows


def narinfo(cache, path):
    return cache / (Path(store_path(path)).name.split("-", 1)[0] + ".narinfo")


def register_roots(config, paths):
    # A fresh root has none of the old user's indirect GC roots. Use Nix's
    # own registration API/GC lock, not an unverified chain of Home symlinks.
    directory = secure_directory(config["gc_roots"], 0o755)
    for index, path in enumerate(paths):
        command("nix-store", "--realise", "--add-root", str(directory / ("root-" + str(index))), store_path(path), timeout=60)
    for old in directory.iterdir():
        if re.fullmatch(r"root-[0-9]+", old.name) and int(old.name[5:]) >= len(paths):
            info = old.lstat()
            if not stat.S_ISLNK(info.st_mode) or info.st_uid != 0:
                raise ValueError("untrusted stale GC root")
            old.unlink()


def restore(config):
    profile, paths = roots(config)
    missing = []
    for path in paths:
        valid = subprocess.run(["nix-store", "--check-validity", path], capture_output=True, timeout=60)
        if valid.returncode != 0 or not Path(path).exists():
            missing.append(path)
    if missing:
        secure_directory("/home/persist", 0o755)
        secure_directory("/home/persist/manifests", 0o755)
        secure_directory(config["cache"], 0o700)
        key = recover_public_key(config)
        verify_missing_cache(config,key,missing)
        # Nix queries every requested source root, even if already valid in the
        # destination. A new image's baked system may never have been exported
        # by the old instance; request only roots that actually need importing.
        command("nix", "--option", "trusted-public-keys", key, "--option", "max-substitution-jobs", "2", "--option", "narinfo-cache-positive-ttl", "0", "--option", "narinfo-cache-negative-ttl", "0", "copy", "--from", "file://" + config["cache"], *missing)
        command("nix-store", "--check-validity", *paths, timeout=60)
    register_roots(config, paths)
    # A concurrent profile update must never let the old profile pass boot gating.
    if roots(config) != (profile, paths):
        raise RuntimeError("profile changed during restoration")
    return {"state": "restored", "profile": profile, "roots": len(paths)}


def signing_public_key(config):
    # Keep secret bytes out of argv, environment, logs and temporary files.
    fd=os.open(config['secret_key'],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_mode&0o077 or info.st_size>4096:
            raise ValueError('untrusted cache signing key')
        result=subprocess.run(['nix','--extra-experimental-features','nix-command','key','convert-secret-to-public'],
                              stdin=stream,capture_output=True,text=True,timeout=15)
    if result.returncode!=0:raise ValueError('cache signing key unavailable or invalid')
    return validated_key(result.stdout.strip())


def recover_public_key(config):
    try:return public_key(config['public_key'])
    except FileNotFoundError:pass
    key=None
    try:manifest=json.loads(trusted_text(config['manifest']))
    except FileNotFoundError:manifest=None
    if manifest is not None:
        if not isinstance(manifest,dict) or type(manifest.get('schema')) is not int or manifest['schema'] not in (1,2):
            raise ValueError('public-key recovery authority unknown')
        key=validated_key(manifest.get('cache_public_key'))
    if key is None:key=signing_public_key(config)
    public=Path(config['public_key']);secure_directory(public.parent,0o755)
    fd=os.open(public,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o444)
    with os.fdopen(fd,'w') as stream:
        stream.write(key+'\n');stream.flush();os.fchmod(stream.fileno(),0o444);os.fsync(stream.fileno())
    fd=os.open(public.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    return key


def ensure_keys(config):
    secret,public=Path(config['secret_key']),Path(config['public_key'])
    if not secret.exists() and not public.exists():
        if any(Path(config['cache']).iterdir()) or Path(config['manifest']).exists():
            raise ValueError('existing cache has lost signing key; refusing implicit rotation')
        command('nix-store','--generate-binary-cache-key','nixos-ec2-persist',str(secret),str(public),timeout=30)
        secret.chmod(0o600);public.chmod(0o444)
    key=recover_public_key(config)
    if signing_public_key(config)!=key:raise ValueError('cache signing and verification keys disagree')
    return key


def publish(path, manifest):
    path = Path(path)
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(json.dumps(manifest, indent=2) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def verify_missing_cache(config,key,missing):
    manager = spot_cache.Cache(config,key,command,lambda:roots(config))
    source = rows_from_json(command('nix','path-info','--store','file://'+config['cache'],'--recursive','--json','--json-format','1',*missing))
    entries = {row['path']:manager.entry(row['path']) for row in source}
    if not set(missing)<=entries.keys():raise ValueError('source cache omitted missing profile roots')
    manager.verify_entries(entries)


def refresh(config):
    base = secure_directory("/home/persist", 0o755)
    secure_directory(base / "root", 0o700)
    secure_directory(base / "manifests", 0o755)
    cache = secure_directory(config['cache'], 0o700)
    key = ensure_keys(config)
    manager = spot_cache.Cache(config, key, command, lambda: roots(config))
    previous = manager.previous()
    try:
        current = manager.verify_current(contents=False)
    except (OSError, ValueError, spot_cache.Unsafe):
        current = None
    if current is not None:
        # No repeated full NAR decompression on every fallback timer. Destructive
        # cleanup and the guard's final pre-action verification always do it.
        repaired = manager.cleanup_repairs()  # also reconcile a crash AFTER checkpoint publication
        cleaned = manager.prune() if manager.garbage_pending() else {}
        return {'state':'current','paths':len(current['entries']),'repair_files_removed':repaired,**cleaned}
    profile, paths = roots(config)
    rows = rows_from_json(command('nix','path-info','--recursive','--json','--json-format','1',*paths,timeout=90))
    register_roots(config, paths)
    by_path = {row['path']:row for row in rows}
    if len(by_path)!=len(rows) or not set(paths)<=by_path.keys():
        raise ValueError('source closure omitted a selected root')
    required = []
    for row in rows:
        try:
            entry = manager.entry(row['path']); info = spot_cache.parse(entry['narinfo'],row['path'])
            if info['NarSize'] != row['narSize'] or info['NarHash'] != spot_cache.nar_hash(row['narHash']):
                raise spot_cache.Unsafe('cached output differs from source store')
        except (OSError,ValueError,spot_cache.Unsafe):required.append(row)
    reserve = config['reserve_bytes']
    if type(reserve) is not int or reserve < 0:raise ValueError('invalid cache reserve')
    needed = sum(row['narSize']+row['narSize']//128+4096 for row in required)
    space = os.statvfs(cache)
    if space.f_bavail*space.f_frsize < needed+reserve:
        manager.invalidate()
        raise RuntimeError('not enough home capacity for a safe cache export')
    parent = previous or manager.adopt()
    manager.repair(list(by_path),expected=by_path)
    manager.invalidate()
    uri = 'file://'+config['cache']+'?compression=zstd&compression-level=3&secret-key='+config['secret_key']
    command('nix','--option','max-substitution-jobs','2','--option','narinfo-cache-positive-ttl','0','--option','narinfo-cache-negative-ttl','0','copy','--to',uri,*paths)
    checkpoint = manager.checkpoint(profile,paths,rows,parent=parent['id'] if parent else None)
    repaired = manager.cleanup_repairs()
    cleaned = manager.prune() if manager.garbage_pending() else {}
    return {'state':'cached','paths':len(rows),'profile':profile,'inventory':checkpoint['id'],
            'repair_files_removed':repaired,**cleaned}


def verify(config):
    manager = spot_cache.Cache(config,recover_public_key(config),command,lambda:roots(config))
    try:
        if signing_public_key(config)!=manager.key:raise ValueError('cache signing and verification keys disagree')
        body = manager.verify_current()
    except Exception:
        manager.invalidate()
        raise
    return {'state':'verified','paths':len(body['entries'])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("restore", "refresh", "verify"))
    parser.add_argument("--config", default="/etc/spot-profile-cache.json")
    args = parser.parse_args()
    config = json.loads(trusted_text(os.path.realpath(args.config)))
    check_home(config)
    runtime = secure_directory("/run/spot-schedule-guard", 0o755)
    fd = os.open(runtime / "lock", os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        check_home(config)  # Drain may have unmounted home while we waited.
        operation = {'restore':restore,'refresh':refresh,'verify':verify}[args.action]
        print(json.dumps(operation(config)))


if __name__ == "__main__":
    main()
