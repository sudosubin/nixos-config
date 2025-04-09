{
  config,
  pkgs,
  lib,
  ...
}:
with lib;

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.services.hammerspoon;

in
{
  options.services.hammerspoon = {
    enable = mkEnableOption "hammerspoon";

    package = mkPackageOption pkgs "hammerspoon" { };

    config = {
      HSUploadCrashData = mkOption {
        type = types.int;
        default = 1;
        description = "Send crash data (required restart)";
      };

      MJConfigFile = mkOption {
        type = types.str;
        default = "~/.hammerspoon/init.lua";
        description = "Config file";
      };

      MJShowDockIconKey = mkOption {
        type = types.int;
        default = 0;
        description = "Show dock icon";
      };

      MJShowMenuIconKey = mkOption {
        type = types.int;
        default = 1;
        description = "Show menu icon";
      };

      SUEnableAutomaticChecks = mkOption {
        type = types.int;
        default = 0;
        description = "Check for updates";
      };

      SUHasLaunchedBefore = mkOption {
        type = types.int;
        default = 1;
        description = "Has launched before";
      };

      SUSendProfileInfo = mkOption {
        type = types.int;
        default = 0;
        description = "Send profile info";
      };
    };
  };

  config = mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enable -> isDarwin;
          message = "Nix hammerspoon only supports darwin.";
        }
      ];
    }

    (mkIf cfg.enable {
      home.packages = [ cfg.package ];

      darwin.defaults."org.hammerspoon.Hammerspoon" = cfg.config;

      launchd.agents.hammerspoon = {
        enable = true;
        config = {
          ProgramArguments = [
            "${config.home.homeDirectory}/Applications/Home Manager Apps/${cfg.package.sourceRoot}/Contents/MacOS/Hammerspoon"
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
