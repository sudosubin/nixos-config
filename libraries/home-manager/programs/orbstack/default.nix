{
  config,
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.services.orbstack;

in
{
  options.services.orbstack = {
    enable = lib.mkEnableOption "orbstack";

    package = lib.mkPackageOption pkgs "orbstack" { };

    config = {
      SUAutomaticallyUpdate = lib.mkOption {
        type = lib.types.int;
        default = 1;
        description = "Automatically download updates";
      };

      SUEnableAutomaticChecks = lib.mkOption {
        type = lib.types.int;
        default = 1;
        description = "Check for updates automatically";
      };

      SUScheduledCheckInterval = lib.mkOption {
        type = lib.types.int;
        default = 14400;
        description = "Update check interval (seconds)";
      };

      SUSendProfileInfo = lib.mkOption {
        type = lib.types.int;
        default = 1;
        description = "Send anonymous system profile";
      };

      activityMonitor_updateFrequency = lib.mkOption {
        type = lib.types.nullOr lib.types.int;
        default = null;
        description = "Activity Monitor update frequency";
      };

      global_holdToQuit = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Hold ⌘Q to quit";
      };

      global_showMenubarExtra = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Show in menu bar";
      };

      global_stayInBackground2 = lib.mkOption {
        type = lib.types.nullOr lib.types.bool;
        default = null;
        description = "Keep running when menu bar app is quit";
      };

      terminal_defaultApp = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "External terminal app";
      };

      updates_optinChannel = lib.mkOption {
        type = lib.types.nullOr lib.types.str;
        default = null;
        description = "Update channel opt-in";
      };
    };
  };

  config = lib.mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enable -> isDarwin;
          message = "Nix orbstack only supports darwin.";
        }
      ];
    }

    (lib.mkIf cfg.enable {
      home.packages = [ cfg.package ];

      targets.darwin.defaults."dev.kdrag0n.MacVirt" = lib.filterAttrs (
        _: value: value != null
      ) cfg.config;
    })
  ];
}
