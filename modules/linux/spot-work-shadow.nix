# NEW non-interactive pilot only; no canonical startup/admission/termination.
{ config, lib, pkgs, ... }:
let
  cfg = config.services.spotWorkShadow;
  identifier = builtins.substring 0 12 (builtins.hashString "sha256" (
    builtins.hashFile "sha256" ./spot_work.py + builtins.hashFile "sha256" ./spot_shadow.py
  ));
  directory = "/var/lib/spot-work-shadow/${identifier}";
  unit = "spot-work-shadow-${identifier}";
  sources = pkgs.runCommand "spot-work-shadow-sources" { } ''
    mkdir -p "$out"
    cp ${./spot_work.py} "$out/spot_work.py"
    cp ${./spot_shadow.py} "$out/spot_shadow.py"
  '';
  settings = pkgs.writeText "spot-work-shadow.json" (builtins.toJSON {
    schema = 1;
    deployment_id = identifier;
    inherit directory;
    uid = 1001;
  });
  tool = pkgs.writeScriptBin "spot-work-shadow" ''
    #!${pkgs.python3}/bin/python3 -I
    import sys,runpy
    sys.dont_write_bytecode = True
    sys.argv[1:1] = ["--config", "${settings}"]
    runpy.run_path("${sources}/spot_shadow.py", run_name="__main__")
  '';
  limits = {
    Type = "exec";
    MemoryMax = "256M";
    MemorySwapMax = 0;
    CPUQuota = "25%";
    OOMPolicy = "kill";
    OOMScoreAdjust = 1000;
    Nice = 19;
    NoNewPrivileges = true;
    PrivateNetwork = true;
    ProtectControlGroups = true;
    RuntimeMaxSec = 120;
    UMask = "0077";
  };
in {
  options.services.spotWorkShadow.enable = lib.mkEnableOption "disarmed warm shadow custody, NEVER full work readiness";
  config = lib.mkIf cfg.enable {
    assertions = [{ assertion = config.services.spotProtectionObserver.enable or false;
      message = "shadow jobs require independently observed protection; never infer it from local empty state"; }];
    environment.systemPackages = [ tool ];
    systemd.tmpfiles.rules = [
      "d /var/lib/spot-work-shadow 0755 root root -"
      "d ${directory} 0700 root root -"
    ];
    systemd.services."${unit}-seed" = {
      description = "Preserve existing shadow records or explicitly seed UNKNOWN; not work readiness";
      after = [ "network-online.target" ];
      serviceConfig = limits // {
        ExecStart = "${tool}/bin/spot-work-shadow seed";
      };
    };
    systemd.services.${unit} = {
      description = "Read-only shadow status; unfinished output and legacy work ALWAYS block";
      requires = [ "${unit}-seed.service" ];
      after = [ "${unit}-seed.service" ];
      serviceConfig = limits // { ExecStart = "${tool}/bin/spot-work-shadow collect"; };
    };
    systemd.timers.${unit} = {
      wantedBy = [ "timers.target" ];
      timerConfig = { OnBootSec = "3min"; OnUnitInactiveSec = "1min"; AccuracySec = "10s"; Persistent = false; };
    };
  };
}
