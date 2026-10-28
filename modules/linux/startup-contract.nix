# Inspect the REAL Linux startup modules without evaluating the unrelated full
# Home Manager/application graph. This is NOT a production system/AMI/OS boot.
# The only fixture is a harmless HM activation package/service; all EC2, home,
# cache, admission, guard, Docker and user-manager definitions are unmodified.
{ nixpkgs }:
let
  evaluated = import (nixpkgs + "/nixos/lib/eval-config.nix") {
    system = "aarch64-linux";
    modules = [
      ./configuration.nix
      (
        { lib, pkgs, ... }:
        {
          options.home-manager.users = lib.mkOption {
            type = lib.types.attrsOf (
              lib.types.submodule {
                options.home.activationPackage = lib.mkOption { type = lib.types.package; };
              }
            );
          };
          config = {
            home-manager.users.sudosubin.home.activationPackage =
              pkgs.writeTextDir "activate" "fixture-only; not executed";
            systemd.services.home-manager-sudosubin.serviceConfig = {
              Type = "oneshot";
              ExecStart = "${pkgs.coreutils}/bin/true";
            };
          };
        }
      )
    ];
  };
  inherit (evaluated) config pkgs;
  names = [
    "spot-work-admission-ready"
    "spot-scale-in-protection-ready"
    "attach-home-volume"
    "spot-profile-cache-restore"
    "spot-workload-startup-ready"
    "spot-schedule-guard"
    "user@1001"
    "docker"
    "home-manager-sudosubin"
    "nix-gc"
    "nix-optimise"
    "docker-prune"
    "amazon-ssm-agent"
  ];
  service =
    name:
    let
      unit = config.systemd.services.${name};
    in
    {
      inherit (unit)
        requires
        after
        before
        wantedBy
        overrideStrategy
        ;
      serviceConfig = builtins.intersectAttrs {
        ExecStart = null;
        ExecCondition = null;
        Type = null;
        RemainAfterExit = null;
        TimeoutStartSec = null;
        StateDirectory = null;
        StateDirectoryMode = null;
      } unit.serviceConfig;
    };
  contract = {
    schema = 1;
    minimal_module_evaluation = true;
    actual_HM_activation_or_OS_boot_verified = false;
    production_armed = config.services.spotScheduleGuard.armed;
    module_sha256 = builtins.listToAttrs (
      map
        (name: {
          inherit name;
          value = builtins.hashFile "sha256" (./. + "/${name}");
        })
        [
          "configuration.nix"
          "hardware-configuration.nix"
          "spot-work.nix"
          "spot-home-volume.nix"
          "spot-profile-cache.nix"
          "spot-schedule-guard.nix"
        ]
    );
    services = builtins.listToAttrs (
      map (name: {
        inherit name;
        value = service name;
      }) names
    );
    home = {
      inherit (config.fileSystems."/home") device fsType options;
    };
  };
in
assert pkgs.lib.assertMsg (builtins.all (
  a: a.assertion
) config.assertions) "startup module assertions failed; no partial contract output";
pkgs.linkFarm "spot-startup-contract" [
  {
    name = "contract.json";
    path = pkgs.writeText "spot-startup-contract.json" (builtins.toJSON contract);
  }
  {
    name = "spot-work";
    path = config.services.spotWork.package;
  }
]
