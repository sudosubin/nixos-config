#!/usr/bin/env python3
"""EC2-resident scale-in guard. ASG owns cron; no external compute or local client.

Default observation mode NEVER releases protection. Replacement must be verified
before arming. Spot/health replacement is outside scale-in protection's scope.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import spot_gateway
import spot_backup
from datetime import datetime, time, timezone
import fcntl
import importlib.util
import json
import os
import re
from pathlib import Path
import stat
import subprocess
import time as clock
import urllib.request
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
RUNTIME = Path("/run/spot-schedule-guard")
WORKERS = {"kiro-cli", "kiro-cli-chat", "bun", "nix", "nix-build", "cargo", "rustc", "java", ".agent-browser-"}
REQUIRED = ("replacement_verified", "closure_restore_verified", "work_tracking_verified", "backup_restore_verified")
_work_spec = importlib.util.spec_from_file_location("spot_work", Path(__file__).with_name("spot_work.py"))
work = importlib.util.module_from_spec(_work_spec)
_work_spec.loader.exec_module(work)


def work_protocol(config):
    return work.Protocol(RUNTIME, uid=config["uid"], gid=config.get("gid", 100))


def maintenance_running():
    units = ("nix-gc.service", "nix-optimise.service", "docker-prune.service")
    jobs = command("systemctl", "list-jobs", "--no-pager", "--no-legend")
    states = command("systemctl", "show", *units, "--property=ActiveState", "--value").split()
    if len(states) != len(units):
        raise ValueError("maintenance state unknown")
    return any(unit in jobs for unit in units) or any(state != "inactive" for state in states)


def running_window(now):
    if now.tzinfo is None:
        raise ValueError("timezone required")
    local = now.astimezone(KST)
    start = time(10, 30) if local.weekday() >= 5 else time(16, 30)
    return local.time() < time(2) or local.time() >= start


def command(*args, timeout=25):
    return subprocess.check_output(args, text=True, timeout=timeout).strip()


def aws(config, service, action, *args):
    env = os.environ.copy()
    for name in ("AWS_PROFILE", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        env.pop(name, None)
    env.update(AWS_CONFIG_FILE="/dev/null", AWS_SHARED_CREDENTIALS_FILE="/dev/null", AWS_PAGER="", AWS_MAX_ATTEMPTS="3")
    if service == 'ec2' and action == 'create-snapshot':
        # EC2 has no ClientToken here. A transport retry could create a second
        # charged copy; recover the tagged attempt instead of blind SDK retry.
        env['AWS_MAX_ATTEMPTS'] = '1'
    result = subprocess.run(["aws", service, action, "--region", config["region"], "--output", "json", *args], capture_output=True, text=True, timeout=30, env=env)
    if result.returncode:
        code = re.search(r'An error occurred \(([A-Za-z0-9_.-]+)\)', result.stderr)
        raise spot_backup.AWSFailure(service, action, code.group(1) if code else 'UnknownTransportOrCliError')
    return json.loads(result.stdout) if result.stdout.strip() else {}


def identity():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request("http://169.254.169.254/latest/api/token", method="PUT", headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"})
    token = opener.open(request, timeout=3).read().decode()
    request = urllib.request.Request("http://169.254.169.254/latest/dynamic/instance-identity/document", headers={"X-aws-ec2-metadata-token": token})
    return json.load(opener.open(request, timeout=3))


def root_json(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022 or info.st_size > 65536:
            raise ValueError("untrusted manifest")
        return json.load(stream)


def probe(config, now):
    mounted = command("findmnt", "-n", "-o", "TARGET", "--target", "/home") == "/home"
    uuid = command("findmnt", "-n", "-o", "UUID", "--target", "/home")
    try:
        manifest = root_json(config["manifest"])
    except (OSError, ValueError):
        manifest = {}
    cache = {}
    if config.get("profile_cache_manifest"):
        try:
            cache = root_json(config["profile_cache_manifest"])
        except (OSError, ValueError):
            pass
    workers = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            name = (proc / "comm").read_text().strip()
            if name in WORKERS:
                workers.append({"pid": int(proc.name), "name": name})
        except OSError:
            continue
    leases = work_protocol(config).blockers(now.timestamp())
    return {
        "mounted": mounted, "uuid": uuid, "manifest": manifest, "profile_cache": cache,
        "system": os.path.realpath("/run/current-system"),
        "profile": os.path.realpath("/home/sudosubin/.nix-profile"),
        "workers": workers, "leases": leases,
        "maintenance": maintenance_running(),
        "gateway": spot_gateway.configured(config, work_protocol(config)).observe() if config.get("gateway") else None,
    }


def reasons(config, now, group, node, sessions, volume):
    result = []
    if config.get("armed") is not True:
        result.append("observation_mode")
    if running_window(now):
        result.append("scheduled_running_window")
    if group["DesiredCapacity"] != 0:
        result.append("asg_not_requesting_scale_in")
    elif now.astimezone(KST).minute % 15:
        result.append("waiting_15_minute_recheck")
    if sessions:
        result.append("active_ssm_sessions")
    if not node["mounted"] or node["uuid"] != config["home_uuid"]:
        result.append("home_not_verified")
    manifest = node["manifest"]
    for key in REQUIRED:
        if manifest.get(key) is not True:
            result.append("prerequisite:" + key)
    if manifest.get("system") != node["system"]:
        result.append("profile_drift")
    if config.get("profile_cache_manifest"):
        cache = node.get("profile_cache", {})
        if (type(cache.get("schema")) is not int or cache["schema"] != 1
                or cache.get("system") != node["system"]
                or cache.get("user_profile") != node["profile"]
                or not isinstance(cache.get("roots"), list)
                or node["profile"] not in cache.get("roots", [])
                or node["system"] not in cache.get("roots", [])):
            result.append("profile_cache_not_current")
    elif manifest.get("user_profile") != node["profile"]:
        result.append("profile_drift")
    if node["workers"]:
        result.append("untracked_workers")
    if node["leases"]:
        result.append("active_or_invalid_leases")
    if node["maintenance"]:
        result.append("maintenance_running")
    if config.get("gateway"):
        gateway = node.get("gateway")
        if not isinstance(gateway, dict) or gateway.get("observable") is not True:
            result.append("gateway_status_unknown")
        elif gateway.get("maintenance_busy") is not False:
            result.append("gateway_maintenance_busy")
    if volume.get("Encrypted") is not True:
        result.append("home_encryption_not_ready")
    if not any(a.get("InstanceId") == config["instance_id"] and a.get("State") == "attached"
               and a.get("DeleteOnTermination") is False for a in volume.get("Attachments", [])):
        result.append("home_attachment_not_verified")
    return result


def protection(config, enabled):
    aws(config, "autoscaling", "set-instance-protection", "--auto-scaling-group-name", config["asg"], "--instance-ids", config["instance_id"], "--protected-from-scale-in" if enabled else "--no-protected-from-scale-in")


def group_state(config):
    groups = aws(config, "autoscaling", "describe-auto-scaling-groups", "--auto-scaling-group-names", config["asg"])["AutoScalingGroups"]
    if len(groups) != 1 or not any(i["InstanceId"] == config["instance_id"] and i["LifecycleState"] == "InService" for i in groups[0]["Instances"]):
        raise ValueError("not an InService member of expected ASG")
    return groups[0]


def startup_protection(config, timeout=240):
    """Do not let new workloads start while ASG membership/protection is pending."""
    deadline = clock.monotonic() + timeout
    while True:
        try:
            group_state(config)
            protection(config, True)
            group = group_state(config)
            if any(i["InstanceId"] == config["instance_id"] and i.get("ProtectedFromScaleIn") is True
                   for i in group["Instances"]):
                status({"state": "startup_protected", "instance_id": config["instance_id"]})
                return
            raise RuntimeError("scale-in protection is not yet confirmed")
        except Exception:
            if clock.monotonic() >= deadline:
                raise
            clock.sleep(5)


def sessions(config):
    return aws(config, "ssm", "describe-sessions", "--state", "Active", "--filters", "key=Target,value=" + config["instance_id"])["Sessions"]


def status(data):
    raw = json.dumps(data, separators=(",", ":"))
    print(raw, flush=True)
    tmp = RUNTIME / "status.tmp"
    tmp.write_text(raw + "\n")
    tmp.replace(RUNTIME / "status.json")


def drain_recheck(config, gateway=None):
    """Recheck the whole mounted-home predicate AFTER new job admission closes."""
    now = datetime.now(timezone.utc)
    group = group_state(config)
    observed_config = config
    if gateway is not None:
        if gateway.stopped:
            # Unavailability is expected ONLY after our bound atomic stop was
            # acknowledged and the manager confirmed this service inactive.
            gateway.manager.assert_stopped()
            observed_config = {key: value for key, value in config.items() if key != "gateway"}
        else:
            gateway.check()
    node = probe(observed_config, now)
    volume = aws(config, "ec2", "describe-volumes", "--volume-ids", config["home_volume"])["Volumes"][0]
    blocked = reasons(observed_config, now, group, node, sessions(config), volume)
    # The cadence controls starting a drain, not how long a valid drain may run.
    blocked = [reason for reason in blocked if reason != "waiting_15_minute_recheck"]
    if blocked:
        raise RuntimeError("shutdown recheck blocked: " + ",".join(blocked))


def shutdown_request_current(config):
    if running_window(datetime.now(timezone.utc)) or group_state(config)["DesiredCapacity"] != 0 or sessions(config):
        raise RuntimeError("shutdown superseded")


def backup_cold_check(config):
    # Check ALL mounts of the configured filesystem, not only /home's target.
    result = subprocess.run(['findmnt', '-rn', '-S', 'UUID='+config['home_uuid'], '-o', 'TARGET'], capture_output=True, timeout=5)
    if result.returncode != 1 or result.stdout.strip():
        raise RuntimeError('home filesystem mounted elsewhere or query unknown')
    volumes = aws(config, 'ec2', 'describe-volumes', '--volume-ids', config['home_volume']).get('Volumes')
    if (not isinstance(volumes, list) or len(volumes) != 1
            or volumes[0].get('VolumeId') != config['home_volume'] or volumes[0].get('Encrypted') is not True):
        raise RuntimeError('cold source identity/encryption changed')
    attachments = volumes[0].get('Attachments')
    if (not isinstance(attachments, list) or len(attachments) != 1
            or attachments[0].get('InstanceId') != config['instance_id']
            or attachments[0].get('State') != 'attached'
            or attachments[0].get('DeleteOnTermination') is not False):
        raise RuntimeError('cold source attachment changed')


def backup_wait_checkpoint(config, protocol, gateway):
    shutdown_request_current(config)
    with protocol.locked():
        if protocol.state() != 'draining' or protocol.blockers_unlocked():
            raise RuntimeError('backup wait cancelled by work or extension')
    if gateway is not None:
        gateway.manager.assert_stopped()
    states = command('systemctl', 'show', 'user@%d.service' % config['uid'], 'docker.service', '--property=ActiveState', '--value').split()
    if states != ['inactive', 'inactive']:
        raise RuntimeError('workload stop state changed during backup')


def drain(config):
    """Only reachable after explicit arming, verified replacement, and idle checks."""
    protocol = work_protocol(config)
    protocol.seal()
    services_stopped = False
    released = False
    gateway = None
    try:
        shutdown_request_current(config)
        backup = spot_backup.configured(config, lambda *args: aws(config, *args),
            lambda: backup_cold_check(config), lambda: backup_wait_checkpoint(config, protocol, gateway))
        backup.prepare()
        gateway = spot_gateway.configured(config, protocol)
        if gateway is not None:
            gateway.acquire()
        drain_recheck(config, gateway)
        if gateway is not None:
            gateway.stop()
        # Mark before issuing stop: a timed-out client does not prove no service
        # was stopped. Rollback must restore any partial transition as well.
        services_stopped = True
        command("systemctl", "stop", "user@%d.service" % config["uid"], "docker.service", timeout=60)
        drain_recheck(config, gateway)
        command("systemctl", "stop", "home.mount", timeout=40)
        check = subprocess.run(["findmnt", "--mountpoint", "/home"], capture_output=True, timeout=5)
        if check.returncode != 1:
            raise RuntimeError("home still mounted or mount query failed")
        command("sync", timeout=20)
        snapshot = backup.capture()
        if snapshot.get('Encrypted') is not True or snapshot.get('State') != 'completed':
            raise RuntimeError('cold backup completion/encryption not verified')
        with protocol.commit():
            shutdown_request_current(config)
            backup.successful(snapshot['SnapshotId'])
            # No extension acknowledged before this lock can be missed. Never
            # call EC2 Stop/Terminate; ASG owns the irreversible transition.
            protection(config, False)
            released = True
        status({"state":"scale_in_released","snapshot_id":snapshot["SnapshotId"]})
    except Exception:
        if released:
            raise  # Never reopen admission after confirmed release.
        protection(config, True)
        group = group_state(config)
        if not any(i["InstanceId"] == config["instance_id"] and i.get("ProtectedFromScaleIn") is True for i in group["Instances"]):
            raise RuntimeError("rollback protection unconfirmed; admission remains closed")
        recovery = protocol.recover_services([gateway.manager.unit]) if gateway is not None else nullcontext()
        with recovery:
            if services_stopped:
                subprocess.run(["systemctl", "start", "home.mount"], check=True, timeout=60)
                subprocess.run(["systemctl", "start", "docker.service", "user@%d.service" % config["uid"]], check=True, timeout=60)
            if gateway is not None:
                gateway.rollback()
        protocol.unseal()
        raise
    finally:
        if gateway is not None:
            gateway.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="/etc/spot-schedule-guard.json")
    parser.add_argument("--protect-only", action="store_true", help="wait for protected InService membership before workloads start")
    args = parser.parse_args()
    config = root_json(os.path.realpath(args.config))
    RUNTIME.mkdir(mode=0o755, exist_ok=True)
    (RUNTIME / "leases").mkdir(mode=0o1733, exist_ok=True)
    os.chmod(RUNTIME / "leases", 0o1733)
    with (RUNTIME / "lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | (0 if args.protect_only else fcntl.LOCK_NB))
        except BlockingIOError:
            return
        try:
            doc = identity()
            if doc["accountId"] != config["account"] or doc["region"] != config["region"]:
                raise ValueError("unexpected AWS identity")
            config["instance_id"] = doc["instanceId"]
            if args.protect_only:
                startup_protection(config)
                return
            group = group_state(config)
            protection(config, True)  # Fail closed before all further checks.
            now = datetime.now(timezone.utc)
            node = probe(config, now)
            current_sessions = sessions(config)
            volume = aws(config, "ec2", "describe-volumes", "--volume-ids", config["home_volume"])["Volumes"][0]
            blocked = reasons(config, now, group, node, current_sessions, volume)
            status({"state":"protected" if blocked else "draining", "checked_at":now.isoformat(), "reasons":blocked, "workers":node["workers"], "sessions":len(current_sessions)})
            if not blocked:
                drain(config)
        except Exception as exc:
            status({"state":"protected_or_unknown","error_type":type(exc).__name__})
            raise


if __name__ == "__main__":
    main()
