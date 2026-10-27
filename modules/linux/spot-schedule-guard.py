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
import spot_cold
import spot_drain
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
_cache_spec = importlib.util.spec_from_file_location('spot_profile_cache', Path(__file__).with_name('spot-profile-cache.py'))
profile_cache = importlib.util.module_from_spec(_cache_spec)
_cache_spec.loader.exec_module(profile_cache)


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
        if (type(cache.get("schema")) is not int or cache["schema"] != 2
                or cache.get('state') != 'verified'
                or not isinstance(cache.get('inventory'),str) or not re.fullmatch(r'[0-9a-f]{32}',cache['inventory'])
                or not isinstance(cache.get('inventory_sha256'),str) or not re.fullmatch(r'[0-9a-f]{64}',cache['inventory_sha256'])
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


def backup_cold_check(config, claim=None):
    # A namespace-local empty findmnt is not cold authority. The real block
    # claim excludes filesystem holders in every namespace until we release it.
    if claim is None:
        raise RuntimeError('kernel filesystem cold custody is required')
    claim.check()
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
    claim.check()  # Retain the same real claim across the API observation.


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


def verify_profile_cache(config):
    # The caller ALREADY holds the shared cache/drain lock. Import the same
    # verifier directly instead of invoking a CLI that would reacquire it.
    if not config.get('profile_cache_config') or not config.get('profile_cache_manifest'):
        raise RuntimeError('cache payload verification is not configured')
    settings = root_json(os.path.realpath(config['profile_cache_config']))
    if (settings.get('manifest') != config['profile_cache_manifest']
            or settings.get('home_uuid') != config['home_uuid']
            or settings.get('system_profile','/run/current-system') != '/run/current-system'):
        raise RuntimeError('cache verification identity differs from guard')
    profile_cache.check_home(settings)
    return profile_cache.verify(settings)


def drain_transaction(config, protocol):
    return spot_drain.Transaction(config, protocol,
        config.get('drain_journal', '/var/lib/spot-schedule-guard/drain.json'))


def capture_services(config):
    units = ['user@%d.service' % config['uid'], 'docker.service']
    result = {unit: command('systemctl', 'show', unit, '--property=ActiveState', '--value') for unit in units}
    if any(state not in {'active', 'inactive'} for state in result.values()):
        raise RuntimeError('workload baseline is transitioning or unknown')
    return result


def verify_recovery_home(config, allow_mount=False):
    # Recheck the real block identity, not a successful old mount command. This
    # restores only the same attached data; never detach, format, or switch it.
    rows = aws(config, 'ec2', 'describe-volumes', '--volume-ids', config['home_volume']).get('Volumes')
    if not isinstance(rows, list) or len(rows) != 1 or rows[0].get('VolumeId') != config['home_volume']:
        raise RuntimeError('recovery source volume unknown')
    attachments = rows[0].get('Attachments')
    if (not isinstance(attachments, list) or len(attachments) != 1
            or attachments[0].get('InstanceId') != config['instance_id']
            or attachments[0].get('State') != 'attached'
            or attachments[0].get('DeleteOnTermination') is not False):
        raise RuntimeError('recovery home attachment changed')
    serial = config['home_volume'].replace('-', '')
    devices = [Path('/dev') / p.parent.parent.name for p in Path('/sys/class/block').glob('nvme*n1/device/serial')
               if p.read_text().strip() == serial]
    if (len(devices) != 1 or Path('/dev/disk/by-uuid', config['home_uuid']).resolve() != devices[0]
            or command('blkid', '-c', '/dev/null', '-s', 'UUID', '-o', 'value', str(devices[0])) != config['home_uuid']):
        raise RuntimeError('recovery EBS serial/filesystem identity changed')
    mounted = subprocess.run(['findmnt', '-rn', '-S', 'UUID='+config['home_uuid'], '-o', 'TARGET'],
                             capture_output=True, text=True, timeout=5)
    if mounted.returncode == 1 and not mounted.stdout.strip() and allow_mount:
        subprocess.run(['systemctl', 'start', 'home.mount'], check=True, timeout=60)
        return verify_recovery_home(config, allow_mount=False)
    if mounted.returncode != 0 or mounted.stdout.split() != ['/home']:
        raise RuntimeError('recovery home is absent, aliased or mounted elsewhere')
    mounted_identity = command('findmnt', '-n', '-o', 'UUID,OPTIONS,FSROOT,SOURCE', '--mountpoint', '/home').split()
    if (len(mounted_identity) != 4 or mounted_identity[0] != config['home_uuid']
            or mounted_identity[2] != '/' or Path(mounted_identity[3]).resolve() != devices[0]
            or 'rw' not in mounted_identity[1].split(',') or 'ro' in mounted_identity[1].split(',')):
        raise RuntimeError('recovery home is not the verified writable filesystem')


def verify_recovery_services(config, before):
    verify_recovery_home(config)
    for unit, state in before.items():
        # Never stop an originally inactive service that someone else started.
        if state == 'active' and command('systemctl', 'show', unit, '--property=ActiveState', '--value') != 'active':
            raise RuntimeError('workload restoration is not confirmed')


class RecoveryOperations:
    def __init__(self, config, protocol):
        self.config, self.protocol = config, protocol

    def group(self):
        return group_state(self.config)

    def request_current(self, group):
        return (not running_window(datetime.now(timezone.utc)) and group['DesiredCapacity'] == 0
                and not sessions(self.config))

    def protect(self):
        protection(self.config, True)
        group = self.group()
        if not any(i['InstanceId'] == self.config['instance_id'] and i.get('ProtectedFromScaleIn') is True
                   for i in group['Instances']):
            raise RuntimeError('recovery protection unconfirmed; admission remains closed')

    def home(self):
        verify_recovery_home(self.config, allow_mount=True)

    def services(self, units):
        subprocess.run(['systemctl', 'start', *units], check=True, timeout=100)

    def gateway(self, snapshot, boot_changed, authority, publish):
        gateway = spot_gateway.configured(self.config, self.protocol, publish=publish)
        if gateway is not None:
            gateway.restore_snapshot(snapshot, boot_changed=boot_changed, authority=authority)

    def verified(self, before):
        verify_recovery_services(self.config, before)


def reconcile_drain(config, protocol, transaction):
    try:
        return transaction.recover(RecoveryOperations(config, protocol))
    finally:
        transaction.close()


def drain(config):
    """Only reachable after explicit arming, verified replacement, and idle checks."""
    protocol = work_protocol(config)
    transaction = drain_transaction(config, protocol)
    services_stopped = False
    released = False
    gateway = None
    cold_claim = None
    try:
        shutdown_request_current(config)
        transaction.begin(capture_services(config))
        shutdown_request_current(config)
        # Verify the FULL generation roster after the atomic fresh seal. A
        # completed job could otherwise add a retained generation between a
        # pre-seal cache check and sealing, without changing the active profile.
        verify_profile_cache(config)
        if protocol.blockers():
            raise RuntimeError('work or extension appeared during cache verification')
        backup = spot_backup.configured(config, lambda *args: aws(config, *args),
            lambda: backup_cold_check(config, cold_claim), lambda: backup_wait_checkpoint(config, protocol, gateway))
        backup.prepare()
        gateway = spot_gateway.configured(config, protocol, publish=transaction.gateway)
        if gateway is not None:
            gateway.acquire()
        drain_recheck(config, gateway)
        if gateway is not None:
            gateway.stop()
        # Mark before issuing stop: a timed-out client does not prove no service
        # was stopped. Rollback must restore any partial transition as well.
        services_stopped = True
        transaction.update('services_stop_requested', services_may_be_stopped=True)
        command("systemctl", "stop", "user@%d.service" % config["uid"], "docker.service", timeout=60)
        transaction.update('services_stopped')
        drain_recheck(config, gateway)
        transaction.update('home_unmount_requested')
        command("systemctl", "stop", "home.mount", timeout=40)
        check = subprocess.run(["findmnt", "--mountpoint", "/home"], capture_output=True, timeout=5)
        if check.returncode != 1:
            raise RuntimeError("home still mounted or mount query failed")
        transaction.update('home_unmounted')
        command("sync", timeout=20)
        # Hold the actual kernel claim, not a check-then-close probe. A hidden
        # namespace/overlay/detached filesystem cannot pass or remount during
        # capture, cold tagging, completion polling or final release checks.
        with spot_cold.configured(config) as cold_claim:
            transaction.update('backing_up')
            snapshot = backup.capture()
            if snapshot.get('Encrypted') is not True or snapshot.get('State') != 'completed':
                raise RuntimeError('cold backup completion/encryption not verified')
            transaction.update('backup_completed', snapshot_id=snapshot['SnapshotId'])
            with protocol.commit():
                shutdown_request_current(config)
                backup.successful(snapshot['SnapshotId'])
                backup_cold_check(config, cold_claim)
                # No extension acknowledged before this lock can be missed.
                # Never call EC2 Stop/Terminate; ASG owns the transition.
                transaction.update('release_requested')
                protection(config, False)
                released = True
                transaction.update('released')
        status({"state":"scale_in_released","snapshot_id":snapshot["SnapshotId"]})
    except Exception:
        if released:
            raise  # Never reopen admission after confirmed release.
        protection(config, True)
        group = group_state(config)
        if not any(i["InstanceId"] == config["instance_id"] and i.get("ProtectedFromScaleIn") is True for i in group["Instances"]):
            raise RuntimeError("rollback protection unconfirmed; admission remains closed")
        if transaction.record is None:
            raise  # No owned intent/fence; never take over another drain.
        if transaction.cancel_unstarted(protected=True):
            raise  # Refused/lost pre-action seal: no new fence or workload IO.
        protocol.reconcile_fence(transaction.record['id'], protected=True)
        transaction.update('recovering')
        recovery = transaction.authority([gateway.manager.unit]) if gateway is not None else nullcontext()
        with recovery:
            if services_stopped:
                subprocess.run(["systemctl", "start", "home.mount"], check=True, timeout=60)
                verify_recovery_home(config)
                restore = [u for u, state in transaction.record['services_before'].items() if state == 'active']
                if restore:
                    subprocess.run(["systemctl", "start", *restore], check=True, timeout=60)
            if gateway is not None:
                gateway.rollback()
        verify_recovery_services(config, transaction.record['services_before'])
        protocol.unseal(transaction.record['id'])
        transaction.update('recovered')
        raise
    finally:
        if gateway is not None:
            gateway.close()
        transaction.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="/etc/spot-schedule-guard.json")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--protect-only", action="store_true", help="wait for protected InService membership before workloads start")
    mode.add_argument("--recover-only", action="store_true", help="reconcile an owned drain without starting a new shutdown")
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
            journal = Path(config.get('drain_journal', '/var/lib/spot-schedule-guard/drain.json'))
            if os.path.lexists(journal):
                protocol = work_protocol(config)
                transaction = drain_transaction(config, protocol)
                try:
                    record = transaction.read()
                except Exception:
                    protection(config, True)
                    raise
                if record is not None and record['phase'] != 'recovered':
                    outcome = reconcile_drain(config, protocol, transaction)
                    status({'state': 'recovery_'+outcome, 'instance_id': config['instance_id']})
                    return  # A restored old drain is never a fresh shutdown approval.
            if args.recover_only:
                startup_protection(config)
                status({'state': 'no_owned_pending_drain', 'instance_id': config['instance_id']})
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
