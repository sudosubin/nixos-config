# Read-only observer independent of work admission / the termination guard.
{ config, lib, pkgs, ... }:
let
  cfg = config.services.spotProtectionObserver;
  identifier = builtins.substring 0 12 (builtins.hashString "sha256" (
    builtins.hashFile "sha256" ./spot_protection.py + builtins.hashFile "sha256" ./spot_observer.py
  ));
  unit = "spot-protection-observer-${identifier}";
  directory = "/var/lib/spot-protection-observer/${identifier}";
  sources = pkgs.runCommand "spot-protection-observer-sources" { } ''
    mkdir -p "$out"
    cp ${./spot_protection.py} "$out/spot_protection.py"
    cp ${./spot_observer.py} "$out/spot_observer.py"
  '';
  settings = pkgs.writeText "spot-protection-observer.json" (builtins.toJSON {
    schema = 1;
    inherit (cfg) account region asg;
    asg_arn = cfg.asgARN;
    deployment_id = identifier;
    state_directory = directory;
  });
in {
  options.services.spotProtectionObserver = {
    enable = lib.mkEnableOption "read-only protected-instance diagnosis, never shutdown authority";
    account = lib.mkOption { type = lib.types.str; default = "537112465379"; };
    region = lib.mkOption { type = lib.types.str; default = "ap-northeast-2"; };
    asg = lib.mkOption { type = lib.types.str; default = "nixos-ec2-asg"; };
    asgARN = lib.mkOption {
      type = lib.types.str;
      default = "arn:aws:autoscaling:ap-northeast-2:537112465379:autoScalingGroup:e8eddd5c-d369-4596-8153-e31e356e5131:autoScalingGroupName/nixos-ec2-asg";
      description = "Exact group UUID; a name-only replacement is observation_unknown.";
    };
  };
  config = lib.mkIf cfg.enable {
    environment.etc."spot-protection-observer-current.json".text = builtins.toJSON {
      deployment_id = identifier;
      observer_unit = "${unit}.service";
      observer_timer = "${unit}.timer";
      status_path = "${directory}/status.json";
      observation_only = true;
      termination_capable = false;
    };
    systemd.tmpfiles.rules = [
      "d /var/lib/spot-protection-observer 0755 root root -"
      "d ${directory} 0700 root root -"
    ];
    systemd.services.${unit} = {
      description = "Read-only ASG protection observation; NEVER unprotects or initializes work";
      after = [ "network-online.target" ];
      wants = [ "network-online.target" ];
      serviceConfig = {
        Type = "exec";
        ExecStart = "${pkgs.python3}/bin/python3 -B -I ${sources}/spot_observer.py --config ${settings}";
        MemoryMax = "256M";
        MemorySwapMax = 0;
        CPUQuota = "25%";
        OOMPolicy = "kill";
        OOMScoreAdjust = 1000;
        Nice = 19;
        NoNewPrivileges = true;
        PrivateNetwork = true;
        ProtectControlGroups = true;
        RuntimeMaxSec = 180;
        UMask = "0077";
        Environment = "PATH=/run/current-system/sw/bin";
      };
    };
    systemd.timers.${unit} = {
      wantedBy = [ "timers.target" ];
      timerConfig = {
        OnBootSec = "2min";
        OnUnitInactiveSec = "5min";
        AccuracySec = "15s";
        Persistent = false;
      };
    };
  };
}
