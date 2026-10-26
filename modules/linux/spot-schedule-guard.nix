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
  guard = pkgs.writeShellApplication {
    name = "spot-schedule-guard";
    runtimeInputs = with pkgs; [
      awscli2
      coreutils
      systemd
      util-linux
    ];
    text = ''
      exec ${pkgs.python3}/bin/python3 ${./spot-schedule-guard.py} "$@"
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
    manifest = "/home/persist/manifests/active.json";
  }
  // lib.optionalAttrs config.services.spotProfileCache.enable {
    profile_cache_manifest = "/home/persist/manifests/profile-cache.json";
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
    environment.systemPackages = [ guard ];
    environment.etc."spot-schedule-guard.json".text = builtins.toJSON settings;
    systemd.tmpfiles.rules = [
      "d /run/spot-schedule-guard 0755 root root -"
      "d /run/spot-schedule-guard/leases 1733 root root -"
    ];
    systemd.services.spot-scale-in-protection-ready = {
      description = "Confirm protected InService membership before attaching production data";
      wantedBy = [ "multi-user.target" ];
      after = [ "network-online.target" ];
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
    systemd.services.spot-schedule-guard = {
      description = "Preserve ASG scale-in protection unless termination is verified safe";
      after = [ "network-online.target" ];
      wants = [ "network-online.target" ];
      serviceConfig = {
        Type = "oneshot";
        ExecStart = "${guard}/bin/spot-schedule-guard";
        TimeoutStartSec = 300;
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
