{
  config,
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.services.hammerspoon2;

in
{
  options.services.hammerspoon2 = {
    enable = lib.mkEnableOption "hammerspoon2";

    package = lib.mkPackageOption pkgs "hammerspoon2" { };

    environment = lib.mkOption {
      type = lib.types.attrsOf lib.types.str;
      default = { };
      description = "Environment variables (inherited by hs.task)";
    };

    config = {
      configLocation = lib.mkOption {
        type = lib.types.str;
        default = "${config.home.homeDirectory}/.config/Hammerspoon2/init.js";
        defaultText = lib.literalExpression ''"''${config.home.homeDirectory}/.config/Hammerspoon2/init.js"'';
        description = "Config file";
      };

      consoleAlpha = lib.mkOption {
        type = lib.types.numbers.between 0.2 1.0;
        default = 1.0;
        description = "Console window opacity";
      };

      consoleAlwaysOnTop = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = "Keep console window on top";
      };

      consoleHistoryLength = lib.mkOption {
        type = lib.types.int;
        default = 100;
        description = "Console history length";
      };

      dockMenuBehaviour = lib.mkOption {
        type = lib.types.enum [
          "dock"
          "menuBar"
          "both"
        ];
        default = "both";
        description = "Show icon in dock, menu bar, or both";
      };

      garbageLoggingEnabled = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = "Enable garbage collection logging (requires minimumLogLevel 0)";
      };

      hasCompletedOnboarding = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = "Skip onboarding";
      };

      minimumLogLevel = lib.mkOption {
        type = lib.types.enum [
          0
          10
          20
          30
          40
          50
          60
        ];
        default = 10;
        description = "Minimum console log level (0 Garbage, 10 Debug, 20 Info, 30 Warning, 40 Error, 50 Console, 60 Autocomplete)";
      };

      relaunchOnReload = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = "Relaunch the app when reloading config";
      };

      SUEnableAutomaticChecks = lib.mkOption {
        type = lib.types.int;
        default = 0;
        description = "Check for updates";
      };

      SUHasLaunchedBefore = lib.mkOption {
        type = lib.types.int;
        default = 1;
        description = "Has launched before";
      };

      SUSendProfileInfo = lib.mkOption {
        type = lib.types.int;
        default = 0;
        description = "Send profile info";
      };
    };
  };

  config = lib.mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enable -> isDarwin;
          message = "Nix hammerspoon2 only supports darwin.";
        }
        {
          assertion = cfg.enable -> config.targets.darwin.copyApps.enable;
          message = "services.hammerspoon2 requires targets.darwin.copyApps.enable.";
        }
      ];
    }

    (lib.mkIf cfg.enable {
      home.packages = [ cfg.package ];

      targets.darwin.defaults."net.tenshu.Hammerspoon-2" = cfg.config;

      launchd.agents.hammerspoon2 = {
        enable = true;
        config = {
          ProgramArguments = [
            "${config.home.homeDirectory}/${config.targets.darwin.copyApps.directory}/Hammerspoon 2.app/Contents/MacOS/Hammerspoon 2"
          ];
          EnvironmentVariables = lib.mkIf (cfg.environment != { }) cfg.environment;
          KeepAlive = true;
          ProcessType = "Interactive";
          StandardOutPath = "${config.xdg.cacheHome}/hammerspoon2.log";
          StandardErrorPath = "${config.xdg.cacheHome}/hammerspoon2.log";
        };
      };
    })
  ];
}
