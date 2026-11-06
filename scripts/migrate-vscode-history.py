#!/usr/bin/env python3
"""Merge VS Code-family Local History offline, without modifying any source.

Dry-run by default. --apply builds and verifies a complete sibling staging tree
before publishing it. Existing destination history is retained as a rollback
copy. This deliberately does not import SQLite state, AI chats or credentials.
"""

import argparse
import hashlib
import json
import math
import os
import posixpath
import shutil
import tempfile
import uuid
from pathlib import Path
from urllib.parse import unquote, urlsplit


class MigrationError(ValueError):
    pass


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def history_hash(uri):
    """VS Code hash(string).toString(16), including UTF-16 and signed int32."""
    value = 149417
    data = uri.encode("utf-16-le")
    for offset in range(0, len(data), 2):
        value = (
            31 * value + int.from_bytes(data[offset : offset + 2], "little")
        ) & 0xFFFFFFFF
    if value >= 0x80000000:
        value -= 0x100000000
    return ("-" if value < 0 else "") + format(abs(value), "x")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path, value):
    fd, temporary = tempfile.mkstemp(prefix=".migration-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def safe_id(value):
    return (
        isinstance(value, str)
        and value not in ("", ".", "..", "entries.json")
        and "/" not in value
        and "\\" not in value
    )


def event_key(uri, metadata, sha256):
    # Same contents at different times, or different source descriptions, are
    # distinct events. IDs are storage addresses, not event identities.
    return (
        uri,
        json.dumps({k: v for k, v in metadata.items() if k != "id"}, sort_keys=True),
        sha256,
    )


def load_history(root, resource_map, rewrites, recover_to):
    records, inventory, recovered = [], {}, []
    if not root.exists():
        return records, inventory, recovered
    if root.is_symlink() or not root.is_dir():
        raise MigrationError(f"History must be a real directory: {root}")
    for bucket in sorted(root.iterdir()):
        if bucket.is_symlink() or not bucket.is_dir():
            raise MigrationError(f"Unexpected item in History: {bucket}")
        files = sorted(bucket.iterdir())
        if any(p.is_symlink() or not p.is_file() for p in files):
            raise MigrationError(f"Unexpected non-file in history bucket: {bucket}")
        if not files:
            continue
        listing = bucket / "entries.json"
        fallback = False
        if listing.exists():
            model = read_json(listing)
            if model.get("version") != 1 or not isinstance(model.get("entries"), list):
                raise MigrationError(f"Unsupported history schema: {listing}")
            uri = model.get("resource")
        else:
            model = {"entries": []}
            uri = resource_map.get(bucket.name)
            if not uri:
                if recover_to is None:
                    raise MigrationError(
                        f"Unmapped bucket {bucket}; provide a resource map or recovery directory"
                    )
                suffixes = {p.suffix for p in files}
                if len(suffixes) != 1:
                    raise MigrationError(f"Ambiguous recovered extension: {bucket}")
                uri = (recover_to / (bucket.name + suffixes.pop())).as_uri()
                fallback = True
        if not isinstance(uri, str) or not urlsplit(uri).scheme:
            raise MigrationError(f"Invalid resource URI: {bucket}")
        if not fallback and history_hash(uri) != bucket.name:
            raise MigrationError(f"Resource URI/hash mismatch: {bucket}")
        original_uri = uri
        for old, new in rewrites:
            if uri.startswith(old):
                uri = new + uri[len(old) :]
                break
        indexed = {}
        for entry in model["entries"]:
            name = entry.get("id")
            timestamp = entry.get("timestamp")
            if not safe_id(name) or name in indexed:
                raise MigrationError(f"Invalid/duplicate entry ID: {listing}")
            if (
                isinstance(timestamp, bool)
                or not isinstance(timestamp, (int, float))
                or not math.isfinite(timestamp)
            ):
                raise MigrationError(f"Invalid timestamp: {listing}")
            if not (bucket / name).is_file():
                raise MigrationError(f"Missing snapshot: {bucket / name}")
            indexed[name] = entry
        for file in files:
            sha256 = digest(file)
            inventory[str(file)] = sha256
            if file == listing:
                continue
            metadata = dict(
                indexed.get(
                    file.name,
                    {
                        "id": file.name,
                        "timestamp": file.stat().st_mtime_ns // 1_000_000,
                        "source": "default.source",
                        "sourceDescription": "Recovered unindexed local history snapshot",
                    },
                )
            )
            record = {
                "resource": uri,
                "original_resource": original_uri,
                "metadata": metadata,
                "path": file,
                "sha256": sha256,
            }
            records.append(record)
            if file.name not in indexed:
                recovered.append(
                    {
                        "path": str(file),
                        "resource": uri,
                        "original_path_unknown": fallback,
                    }
                )
    return records, inventory, recovered


def snapshot_id(preferred, uri, sha256, used):
    extension = posixpath.splitext(unquote(urlsplit(uri).path).rsplit("/", 1)[-1])[1]
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

    def valid(name):
        stem = name[:4]
        return (
            len(stem) == 4
            and all(c in alphabet for c in stem)
            and name[4:] == extension
        )

    if valid(preferred) and preferred.casefold() not in used:
        return preferred
    seed = int(sha256[:16], 16)
    for attempt in range(62**4):
        number = (seed + attempt) % (62**4)
        chars = []
        for _ in range(4):
            chars.append(alphabet[number % 62])
            number //= 62
        name = "".join(chars) + extension
        if name.casefold() not in used:
            return name
    raise MigrationError("Exhausted native four-character snapshot IDs")


def migrate(
    sources,
    destination,
    *,
    apply=False,
    audit_dir=None,
    resource_map=None,
    rewrites=(),
    recover_to=None,
):
    sources = [Path(p).expanduser().absolute() for p in sources]
    destination = Path(destination).expanduser().absolute()
    recover_to = Path(recover_to).expanduser().absolute() if recover_to else None
    roots = [destination, *sources]
    for index, root in enumerate(roots):
        for other in roots[:index]:
            a, b = root.resolve(), other.resolve()
            if a == b or a in b.parents or b in a.parents:
                raise MigrationError(
                    "History roots must be distinct and non-overlapping"
                )
    if not sources or any(not p.is_dir() for p in sources):
        raise MigrationError("Every source History directory must exist")
    if recover_to and any(
        recover_to.resolve() == p.resolve()
        or p.resolve() in recover_to.resolve().parents
        for p in roots
    ):
        raise MigrationError("Recovered files must be outside every History tree")
    if apply and audit_dir is None:
        raise MigrationError("--audit-dir is required when applying")
    groups, events, inventory, recovered, provenance = {}, {}, {}, [], []
    original_count = 0
    for index, root in enumerate(roots):
        # Never reinterpret existing destination records or infer their paths.
        records, files, repairs = load_history(
            root,
            resource_map or {},
            rewrites if index else (),
            recover_to if index else None,
        )
        if index == 0:
            original_count = len(records)
        inventory.update(files)
        recovered.extend(repairs)
        for record in records:
            uri = record["resource"]
            key = event_key(uri, record["metadata"], record["sha256"])
            if key not in events:
                group = groups.setdefault(uri, {"entries": [], "used": set()})
                name = snapshot_id(
                    record["metadata"]["id"], uri, record["sha256"], group["used"]
                )
                metadata = {**record["metadata"], "id": name}
                group["used"].add(name.casefold())
                group["entries"].append({**record, "metadata": metadata})
                events[key] = (history_hash(uri), name)
            bucket, name = events[key]
            provenance.append(
                {
                    "source": str(record["path"]),
                    "original_resource": record["original_resource"],
                    "resource": uri,
                    "bucket": bucket,
                    "id": name,
                    "sha256": record["sha256"],
                }
            )
    buckets = {}
    for uri in groups:
        key = history_hash(uri)
        if key in buckets:
            raise MigrationError(
                "Resource hash collision: cannot publish a lossy native History tree"
            )
        buckets[key] = uri
    report = {
        "applied": False,
        "sources": [str(p) for p in sources],
        "destination": str(destination),
        "resources": len(groups),
        "input_snapshots": len(provenance),
        "destination_snapshots_before": original_count,
        "output_snapshots": len(events),
        "deduplicated_events": len(provenance) - len(events),
        "max_entries_per_file": max(
            (len(g["entries"]) for g in groups.values()), default=0
        ),
        "recovered_unindexed": recovered,
        "provenance": provenance,
    }
    if not apply:
        return report
    audit_dir = Path(audit_dir).expanduser().absolute()
    if any(
        audit_dir.resolve() == p.resolve() or p.resolve() in audit_dir.resolve().parents
        for p in roots
    ):
        raise MigrationError("Audit directory must be outside every History tree")
    audit_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".history-staging-", dir=destination.parent))
    rollback = None
    try:
        for uri, group in groups.items():
            folder = staging / history_hash(uri)
            folder.mkdir(mode=0o700)
            entries = sorted(
                group["entries"],
                key=lambda r: (r["metadata"]["timestamp"], r["metadata"]["id"]),
            )
            for record in entries:
                target = folder / record["metadata"]["id"]
                shutil.copy2(record["path"], target)
                target.chmod(0o600)
                if digest(target) != record["sha256"]:
                    raise MigrationError(f"Copy verification failed: {target}")
            atomic_json(
                folder / "entries.json",
                {
                    "version": 1,
                    "resource": uri,
                    "entries": [r["metadata"] for r in entries],
                },
            )
        checked, _, _ = load_history(staging, {}, (), None)
        actual = {event_key(r["resource"], r["metadata"], r["sha256"]) for r in checked}
        if actual != set(events):
            raise MigrationError("Staged event verification failed")
        current_files = {
            str(file)
            for root in roots
            if root.exists()
            for bucket in root.iterdir()
            if bucket.is_dir()
            for file in bucket.iterdir()
            if file.is_file()
        }
        if current_files != set(inventory):
            raise MigrationError(
                "History files changed during migration; close all editors and retry"
            )
        for file, sha256 in inventory.items():
            if not Path(file).is_file() or digest(Path(file)) != sha256:
                raise MigrationError(
                    "History changed during migration; close all editors and retry"
                )
        # Recovery copies are new, clearly named files, never original project files.
        if recover_to:
            recover_to.mkdir(parents=True, exist_ok=True, mode=0o700)
            unknown_uris = {
                r["resource"] for r in recovered if r["original_path_unknown"]
            }
            for uri in unknown_uris:
                target = Path(unquote(urlsplit(uri).path))
                latest = max(
                    groups[uri]["entries"], key=lambda r: r["metadata"]["timestamp"]
                )
                if not target.exists():
                    with (
                        target.open("xb") as stream,
                        latest["path"].open("rb") as source,
                    ):
                        shutil.copyfileobj(source, stream)
                    target.chmod(0o600)
        if destination.exists():
            rollback = destination.with_name(
                destination.name + ".before-migration-" + uuid.uuid4().hex
            )
            destination.rename(rollback)
        try:
            staging.rename(destination)
        except BaseException:
            if rollback:
                rollback.rename(destination)
            raise
        report["applied"] = True
        report["rollback"] = str(rollback) if rollback else None
        report["source_inventory"] = inventory
        atomic_json(audit_dir / ("history-merge-" + uuid.uuid4().hex + ".json"), report)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument(
        "--resource-map",
        type=Path,
        help="JSON mapping of missing-metadata bucket hashes to verified original URIs",
    )
    parser.add_argument(
        "--rewrite-uri-prefix", action="append", default=[], metavar="OLD=NEW"
    )
    parser.add_argument(
        "--recover-unmapped-to",
        type=Path,
        help="Preserve otherwise unmappable snapshots under clearly named recovery files",
    )
    parser.add_argument("--audit-dir", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        rewrites = []
        for rewrite in args.rewrite_uri_prefix:
            old, new = rewrite.split("=", 1)
            if not old or not new:
                raise MigrationError("URI rewrite prefixes must be nonempty")
            rewrites.append((old, new))
        report = migrate(
            args.source,
            args.destination,
            apply=args.apply,
            audit_dir=args.audit_dir,
            resource_map=read_json(args.resource_map) if args.resource_map else {},
            rewrites=rewrites,
            recover_to=args.recover_unmapped_to,
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Migration aborted: {error}\n")
    summary = {
        k: v
        for k, v in report.items()
        if k not in ("provenance", "source_inventory", "recovered_unindexed")
    }
    summary["recovered_unindexed_count"] = len(report["recovered_unindexed"])
    summary["original_path_unknown_count"] = sum(
        r["original_path_unknown"] for r in report["recovered_unindexed"]
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
