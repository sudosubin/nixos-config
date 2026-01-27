{
  config,
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.services.hammerspoon;

in
{
  options.services.hammerspoon = {
    enable = lib.mkEnableOption "hammerspoon";

    package = lib.mkPackageOption pkgs "hammerspoon" { };

    config = {
      HSUploadCrashData = lib.mkOption {
        type = lib.types.int;
        default = 1;
        description = "Send crash data (required restart)";
      };

      MJConfigFile = lib.mkOption {
        type = lib.types.str;
        default = "~/.hammerspoon/init.lua";
        description = "Config file";
      };

      MJShowDockIconKey = lib.mkOption {
        type = lib.types.int;
        default = 0;
        description = "Show dock icon";
      };

      MJShowMenuIconKey = lib.mkOption {
        type = lib.types.int;
        default = 1;
        description = "Show menu icon";
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
          message = "Nix hammerspoon only supports darwin.";
        }
      ];
    }

    (lib.mkIf cfg.enable {
      home.packages = [ cfg.package ];

      targets.darwin.defaults."org.hammerspoon.Hammerspoon" = cfg.config;

      launchd.agents.hammerspoon = {
        enable = true;
        config = {
          ProgramArguments = [
            "${config.home.homeDirectory}/Applications/Home Manager Apps/Hammerspoon.app/Contents/MacOS/Hammerspoon"
          ];
          KeepAlive = true;
          ProcessType = "Interactive";
          StandardOutPath = "${config.xdg.cacheHome}/hammerspoon.log";
          StandardErrorPath = "${config.xdg.cacheHome}/hammerspoon.log";
        };
      };
    })
  ];
}
