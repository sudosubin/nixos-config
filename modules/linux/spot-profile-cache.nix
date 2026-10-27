# Package/profile persistence lives on AWS EBS, never on an operator laptop.
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.spotProfileCache;
  sources = pkgs.runCommand "spot-profile-cache-sources" { } ''
    mkdir -p "$out"
    cp ${./spot-profile-cache.py} "$out/spot-profile-cache.py"
    cp ${./spot_cache.py} "$out/spot_cache.py"
  '';
  tool = pkgs.writeShellApplication {
    name = "spot-profile-cache";
    runtimeInputs = [
      pkgs.nix
      pkgs.openssl
      pkgs.util-linux
    ];
    text = ''
      export NIX_CONFIG='experimental-features = nix-command flakes'
      exec ${pkgs.python3}/bin/python3 ${sources}/spot-profile-cache.py "$@"
    '';
  };
  settings = {
    home_uuid = config.services.spotScheduleGuard.homeUUID;
    profile = "/home/sudosubin/.nix-profile";
    home_profile = "/home/sudosubin/.local/state/nix/profiles/home-manager";
    home_generations = [ (toString config.home-manager.users.sudosubin.home.activationPackage) ];
    cache = "/home/persist/nix-closure-cache";
    public_key = "/home/persist/manifests/nix-cache-key.pub";
    secret_key = "/home/persist/root/nix-cache-key.sec";
    manifest = "/home/persist/manifests/profile-cache.json";
    gc_roots = "/nix/var/nix/gcroots/spot-profile-cache";
    reserve_bytes = cfg.reserveBytes;
    uid = 1001;
    generation_directories = [
      "/home/sudosubin/.local/state/nix/profiles"
      "/nix/var/nix/profiles/per-user/sudosubin"
    ];
    keep_checkpoints = cfg.keepCheckpoints;
    prune_grace_seconds = cfg.pruneGraceSeconds;
  };
  common = {
    requires = [ "home.mount" ];
    after = [
      "home.mount"
      "nix-daemon.socket"
    ];
    wants = [ "nix-daemon.socket" ];
    unitConfig.ConditionPathIsMountPoint = "/home";
    serviceConfig = {
      Type = "oneshot";
      UMask = "0077";
      Nice = 19;
      IOSchedulingClass = "idle";
      MemoryMax = "1G";
      TimeoutStartSec = 1200;
    };
  };
in
{
  options.services.spotProfileCache = {
    enable = lib.mkEnableOption "persistent signed Nix profile cache and boot restoration";
    keepCheckpoints = lib.mkOption {
      type = lib.types.ints.between 2 100;
      default = 2;
      description = "Retain verified checkpoints as well as EVERY retained user profile generation.";
    };
    pruneGraceSeconds = lib.mkOption {
      type = lib.types.ints.unsigned;
      default = 86400;
      description = "Minimum age before inventory-attested obsolete cache objects may be pruned.";
    };
    reserveBytes = lib.mkOption {
      type = lib.types.ints.unsigned;
      default = 8 * 1024 * 1024 * 1024;
      description = "Home space that cache export must leave free.";
    };
  };
  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ tool ];
    environment.etc."spot-profile-cache.json".text = builtins.toJSON settings;
    systemd.services.spot-profile-cache-restore = lib.recursiveUpdate common {
      description = "Restore persistent Nix profiles before user workloads";
      wantedBy = [ "multi-user.target" ];
      before = [
        "home-manager-sudosubin.service"
        "user@1001.service"
        "docker.service"
      ];
      serviceConfig = {
        ExecStart = "${tool}/bin/spot-profile-cache restore";
        RemainAfterExit = true;
      };
    };
    systemd.services.spot-profile-cache-refresh = lib.recursiveUpdate common {
      description = "Publish a complete signed Nix profile checkpoint on EBS";
      serviceConfig.ExecStart = "${tool}/bin/spot-profile-cache refresh";
    };
    systemd.paths.spot-profile-cache-refresh = {
      description = "Checkpoint user profile generation changes";
      wantedBy = [ "multi-user.target" ];
      requires = [ "home.mount" ];
      after = [ "home.mount" ];
      pathConfig = {
        PathChanged = "/home/sudosubin/.local/state/nix/profiles";
        Unit = "spot-profile-cache-refresh.service";
      };
    };
    # A timer catches events coalesced while the exporter was already running.
    systemd.timers.spot-profile-cache-refresh = {
      wantedBy = [ "timers.target" ];
      timerConfig = {
        OnBootSec = "2min";
        OnUnitInactiveSec = "5min";
        Persistent = false;
      };
    };
    systemd.services.home-manager-sudosubin = {
      requires = [ "spot-profile-cache-restore.service" ];
      after = [ "spot-profile-cache-restore.service" ];
    };
    systemd.services."user@1001" = {
      requires = [ "spot-profile-cache-restore.service" ];
      after = [ "spot-profile-cache-restore.service" ];
    };
    systemd.services.docker = {
      requires = [ "spot-profile-cache-restore.service" ];
      after = [ "spot-profile-cache-restore.service" ];
    };
    # Missing home must not make GC forget profiles kept on that home volume.
    systemd.services.nix-gc = {
      requires = [
        "home.mount"
        "spot-profile-cache-restore.service"
      ];
      after = [
        "home.mount"
        "spot-profile-cache-restore.service"
      ];
    };
  };
}
