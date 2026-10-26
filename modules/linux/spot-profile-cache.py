#!/usr/bin/env python3
"""Restore/cache persistent Nix profiles without Git, network caches, or a laptop.

The logical store remains /nix/store. Only NAR data and profile metadata persist
on /home. Never run activation scripts from the cache. A failed export never
publishes a new manifest. Share the shutdown guard's lock during all cache I/O.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import subprocess

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
    key = trusted_text(path, limit=4096).strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]+:[A-Za-z0-9+/=]+", key):
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
    result = [store_path(os.path.realpath("/run/current-system"))]
    profile = store_path(os.path.realpath(config["profile"]))
    result.append(profile)
    for name in config.get("home_generations", []):
        result.append(store_path(name))
    extra = Path(config["home_profile"])
    if extra.is_symlink() or extra.exists():
        result.append(store_path(os.path.realpath(extra)))
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
    valid = subprocess.run(["nix-store", "--check-validity", *paths], capture_output=True, timeout=60)
    if valid.returncode != 0 or not all(Path(p).exists() for p in paths):
        secure_directory("/home/persist", 0o755)
        secure_directory("/home/persist/manifests", 0o755)
        secure_directory(config["cache"], 0o700)
        key = public_key(config["public_key"])
        command("nix", "--option", "trusted-public-keys", key, "--option", "max-substitution-jobs", "2", "copy", "--from", "file://" + config["cache"], *paths)
        command("nix-store", "--check-validity", *paths, timeout=60)
    register_roots(config, paths)
    # A concurrent profile update must never let the old profile pass boot gating.
    if roots(config) != (profile, paths):
        raise RuntimeError("profile changed during restoration")
    return {"state": "restored", "profile": profile, "roots": len(paths)}


def ensure_keys(config):
    secret, public = Path(config["secret_key"]), Path(config["public_key"])
    if not secret.exists() and not public.exists():
        command("nix-store", "--generate-binary-cache-key", "nixos-ec2-persist", str(secret), str(public), timeout=30)
        secret.chmod(0o600)
        public.chmod(0o444)
    trusted_text(secret, secret=True, limit=4096)
    return public_key(public)


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


def refresh(config):
    base = secure_directory("/home/persist", 0o755)
    secure_directory(base / "root", 0o700)
    secure_directory(base / "manifests", 0o755)
    cache = secure_directory(config["cache"], 0o700)
    key = ensure_keys(config)
    profile, paths = roots(config)
    rows = rows_from_json(command("nix", "path-info", "--recursive", "--json", *paths, timeout=90))
    register_roots(config, paths)
    missing_bytes = sum(row["narSize"] for row in rows if not narinfo(cache, row["path"]).exists())
    space = os.statvfs(cache)
    if space.f_bavail * space.f_frsize < missing_bytes + config["reserve_bytes"]:
        raise RuntimeError("not enough home capacity for a safe cache export")
    uri = "file://" + config["cache"] + "?compression=zstd&compression-level=3&secret-key=" + config["secret_key"]
    command("nix", "--option", "max-substitution-jobs", "2", "copy", "--to", uri, *paths)
    for row in rows:
        # Actual cryptographic verification is done by Nix on import; require the
        # configured signer for every exported path, including custom generations.
        info = trusted_text(narinfo(cache, row["path"]), limit=1048576)
        if not any(line.startswith("Sig: " + key.split(":", 1)[0] + ":") for line in info.splitlines()):
            raise ValueError("incomplete or unsigned export")
    if roots(config) != (profile, paths):
        raise RuntimeError("profile changed during export; retry on next timer")
    manifest = {"schema": 1, "exported_at": datetime.now(timezone.utc).isoformat(), "system": os.path.realpath("/run/current-system"), "user_profile": profile, "roots": paths, "cached_paths": len(rows), "cache_public_key": key}
    publish(config["manifest"], manifest)
    return {"state": "cached", "paths": len(rows), "profile": profile}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("restore", "refresh"))
    parser.add_argument("--config", default="/etc/spot-profile-cache.json")
    args = parser.parse_args()
    config = json.loads(trusted_text(os.path.realpath(args.config)))
    check_home(config)
    runtime = secure_directory("/run/spot-schedule-guard", 0o755)
    fd = os.open(runtime / "lock", os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        check_home(config)  # Drain may have unmounted home while we waited.
        print(json.dumps(restore(config) if args.action == "restore" else refresh(config)))


if __name__ == "__main__":
    main()
