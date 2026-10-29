# Disposable REAL NixOS boot using the maintained startup/storage/cache modules.
# Only HM is an inert public fixture. This cannot prove real HM/app restoration.
# No production data, EIP, SSH keys, model config or arming authority is included.
{ nixpkgs, scope, homeVolume, homeUUID }:
let
  name = "nixos-spot-proof-${scope}";
  evaluated = import (nixpkgs + "/nixos/lib/eval-config.nix") {
    system = "aarch64-linux";
    modules = [
      ./configuration.nix
      ({ config, lib, pkgs, ... }: {
        options.home-manager.users = lib.mkOption {
          type = lib.types.attrsOf (lib.types.submodule {
            options.home.activationPackage = lib.mkOption { type = lib.types.package; };
          });
        };
        config = {
          services.spotScheduleGuard = {
            asg = name;
            inherit homeVolume homeUUID;
            armed = lib.mkForce false;
          };
          # Home/EBS startup is tested here. Production EIP restoration is a
          # separate still-required trial; this fixture must never touch it.
          systemd.services.associate-eip.enable = lib.mkForce false;
          services.openssh.enable = lib.mkForce false;
          users.users.sudosubin.openssh.authorizedKeys.keys = lib.mkForce [];
          zramSwap.enable = lib.mkForce false;
          virtualisation.docker.autoPrune.enable = lib.mkForce false;
          home-manager.users.sudosubin.home.activationPackage =
            pkgs.writeTextDir "activate" "public inert HM fixture; never real user activation";
          systemd.services.home-manager-sudosubin = {
            wantedBy = [ "multi-user.target" ];
            serviceConfig = {
              Type = "oneshot";
              RemainAfterExit = true;
              ExecStart = pkgs.writeShellScript "recovery-fixture-HM" ''
                set -eu
                [ "$(${pkgs.util-linux}/bin/findmnt -n -o UUID --mountpoint /home)" = '${homeUUID}' ]
                ${config.services.spotWork.package}/bin/spot-work check-service-open
                printf '%s\n' '${scope}' > /run/spot-recovery-HM-fixture-started
              '';
            };
          };
          environment.systemPackages = [ pkgs.hello ];
          environment.etc."spot-recovery-fixture.json".text = builtins.toJSON {
            inherit scope homeVolume homeUUID;
            fixture = "real OS/home/cache/user-manager/Docker; inert HM only";
            actual_HM_activation_verified = false;
            production_EIP_verified = false;
            work_tracking_verified = false;
            armed = false;
            goal_complete = false;
          };
        };
      })
    ];
  };
in
assert builtins.match "[0-9a-f]{12}" scope != null;
assert builtins.match "vol-[0-9a-f]{17}" homeVolume != null;
assert !(builtins.elem homeVolume [ "vol-065729ef75553a7ec" "vol-09fea2ff4615b1088" "vol-0b529abe51df1eca1" ]);
assert builtins.match "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}" homeUUID != null;
assert !(builtins.elem homeUUID [ "e47b82eb-22d2-4b12-9e58-92d5aabfbc65" "fda703d2-55d7-4399-9aff-a589afa645a4" ]);
assert evaluated.pkgs.lib.assertMsg (builtins.all (a: a.assertion) evaluated.config.assertions) "recovery fixture assertions failed";
evaluated.config.system.build.toplevel
