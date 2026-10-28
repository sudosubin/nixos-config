# AWS ASG owns all scheduled actions. This guard runs ONLY inside the existing EC2.
# No Lambda, Step Functions, DynamoDB, Scheduler, SNS, paid metrics, or local cron.
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.spotScheduleGuard;
  sources = pkgs.runCommand "spot-schedule-sources" { } ''
    mkdir -p "$out"
    cp ${./spot-schedule-guard.py} "$out/spot-schedule-guard.py"
    cp ${./spot_work.py} "$out/spot_work.py"
    cp ${./spot_gateway.py} "$out/spot_gateway.py"
    cp ${./spot-gateway-rpc.mjs} "$out/spot-gateway-rpc.mjs"
    cp ${./spot_backup.py} "$out/spot_backup.py"
    cp ${./spot_cold.py} "$out/spot_cold.py"
    cp ${./spot_drain.py} "$out/spot_drain.py"
    cp ${./spot-profile-cache.py} "$out/spot-profile-cache.py"
    cp ${./spot_cache.py} "$out/spot_cache.py"
  '';
  guard = pkgs.writeShellApplication {
    name = "spot-schedule-guard";
    runtimeInputs = with pkgs; [
      awscli2
      coreutils
      nix
      openssl
      systemd
      util-linux
    ];
    text = ''
      exec ${pkgs.python3}/bin/python3 ${sources}/spot-schedule-guard.py "$@"
    '';
  };
  backupPolicy = pkgs.writeShellApplication {
    name = "spot-backup-policy";
    text = ''
      exec ${pkgs.python3}/bin/python3 ${./spot-backup-iam.py} \
        --account ${lib.escapeShellArg cfg.account} --region ${lib.escapeShellArg cfg.region} \
        --volume ${lib.escapeShellArg cfg.homeVolume} --set ${lib.escapeShellArg cfg.backupSet}
    '';
  };
  settings = {
    inherit (cfg)
      armed
      account
      region
      asg
      ;
    home_uuid = cfg.homeUUID;
    home_volume = cfg.homeVolume;
    uid = 1001;
    gid = 100;
    manifest = "/home/persist/manifests/active.json";
    drain_journal = "/var/lib/spot-schedule-guard/drain.json";
    backup = {
      set = cfg.backupSet;
      keep = 3;
      journal = "/var/lib/spot-schedule-guard/backup.json";
    };
  }
  // lib.optionalAttrs config.services.spotProfileCache.enable {
    profile_cache_manifest = "/home/persist/manifests/profile-cache.json";
    profile_cache_config = "/etc/spot-profile-cache.json";
  }
  // lib.optionalAttrs config.services.spotGateway.enable {
    gateway = {
      inherit (config.services.spotGateway) unit node;
      vendor_dir = config.services.spotGateway.vendorDirectory;
      startup_check = "${config.services.spotWork.package}/bin/spot-work";
    };
  };
in
{
  options.services.spotScheduleGuard = {
    enable = lib.mkEnableOption "fail-closed, EC2-resident ASG scale-in guard";
    armed = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Release scale-in protection only after all restoration/work-tracking prerequisites pass.";
    };
    account = lib.mkOption {
      type = lib.types.str;
      default = "537112465379";
    };
    region = lib.mkOption {
      type = lib.types.str;
      default = "ap-northeast-2";
    };
    asg = lib.mkOption {
      type = lib.types.str;
      default = "nixos-ec2-asg";
    };
    backupSet = lib.mkOption {
      type = lib.types.strMatching "[a-zA-Z0-9_.-]{1,100}";
      default = "${cfg.asg}-home";
    };
    homeVolume = lib.mkOption {
      type = lib.types.str;
      default = "vol-09fea2ff4615b1088";
    };
    homeUUID = lib.mkOption {
      type = lib.types.str;
      default = "e47b82eb-22d2-4b12-9e58-92d5aabfbc65";
    };
  };
  config = lib.mkIf cfg.enable {
    services.spotWork.enable = true;
    environment.systemPackages = [
      guard
      backupPolicy
    ];
    environment.etc."spot-schedule-guard.json".text = builtins.toJSON settings;
    systemd.services.spot-scale-in-protection-ready = {
      description = "Confirm protected InService membership before attaching production data";
      wantedBy = [ "multi-user.target" ];
      requires = [ "spot-work-admission-ready.service" ];
      after = [
        "network-online.target"
        "spot-work-admission-ready.service"
      ];
      wants = [ "network-online.target" ];
      before = [ "attach-home-volume.service" ];
      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        ExecStart = "${guard}/bin/spot-schedule-guard --protect-only";
        TimeoutStartSec = 360;
        UMask = "0077";
      };
    };
    systemd.services.spot-workload-startup-ready = {
      description = "Verify protected home/cache and inspect durable drain before admitting boot workloads";
      wantedBy = [ "multi-user.target" ];
      requires = [
        "spot-work-admission-ready.service"
        "spot-scale-in-protection-ready.service"
        "home.mount"
      ]
      ++ lib.optional config.services.spotProfileCache.enable "spot-profile-cache-restore.service";
      after = [
        "spot-work-admission-ready.service"
        "spot-scale-in-protection-ready.service"
        "home.mount"
      ]
      ++ lib.optional config.services.spotProfileCache.enable "spot-profile-cache-restore.service";
      before = [
        "user@1001.service"
        "docker.service"
        "home-manager-sudosubin.service"
      ];
      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        ExecStart = "${guard}/bin/spot-schedule-guard --startup-only";
        TimeoutStartSec = "infinity";
        StateDirectory = "spot-schedule-guard";
        StateDirectoryMode = "0700";
        UMask = "0077";
        WorkingDirectory = "/run/spot-schedule-guard";
      };
    };
    systemd.services.spot-schedule-guard = {
      description = "Preserve ASG scale-in protection unless termination is verified safe";
      requires = [ "spot-work-admission-ready.service" ];
      after = [
        "network-online.target"
        "spot-work-admission-ready.service"
      ];
      wants = [ "network-online.target" ];
      serviceConfig = {
        Type = "oneshot";
        ExecStart = "${guard}/bin/spot-schedule-guard";
        # A timeout must not kill the coordinator during cold backup/recovery.
        # Individual API observations remain bounded and fail closed.
        TimeoutStartSec = "infinity";
        StateDirectory = "spot-schedule-guard";
        StateDirectoryMode = "0700";
        UMask = "0077";
        Nice = 10;
        WorkingDirectory = "/run/spot-schedule-guard";
      };
    };
    systemd.timers.spot-schedule-guard = {
      wantedBy = [ "timers.target" ];
      timerConfig = {
        OnBootSec = "1min";
        OnUnitInactiveSec = "1min";
        AccuracySec = "10s";
      };
    };
    # Terminal notice uses the instance's journal/TTY only; no paid alert service.
    systemd.services.spot-schedule-warning = {
      description = "Notify connected users before guarded ASG scale-in";
      serviceConfig.Type = "oneshot";
      script = ''
        ${pkgs.util-linux}/bin/wall --nobanner \
          'Scheduled ASG scale-in at 02:00 KST. Active sessions/jobs retain protection; no forced shutdown.'
      '';
    };
    systemd.timers.spot-schedule-warning = {
      wantedBy = [ "timers.target" ];
      timerConfig = {
        OnCalendar = "*-*-* 01:45:00 Asia/Seoul";
        Persistent = false;
      };
    };
  };
}
