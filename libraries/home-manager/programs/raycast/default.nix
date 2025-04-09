{
  config,
  pkgs,
  lib,
  ...
}:
with lib;

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.services.raycast;

in
{
  options.services.raycast = {
    enable = mkEnableOption "raycast";

    package = mkPackageOption pkgs "raycast" { };

    config = {
      navigationCommandStyleIdentifierKey = mkOption {
        type = types.str;
        default = "macos";
        description = "Navigation Bindings";
      };

      raycastGlobalHotkey = mkOption {
        type = types.str;
        default = "Option-49";
        description = "Raycast Hotkey";
      };

      raycastPreferredWindowMode = mkOption {
        type = types.str;
        default = "default";
        description = "Window Mode";
      };
    };
  };

  config = mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enable -> isDarwin;
          message = "Nix raycast only supports darwin.";
        }
      ];
    }

    (mkIf cfg.enable {
      home.packages = [ cfg.package ];

      darwin.defaults."com.raycast.macos" = cfg.config;

      launchd.agents.raycast = {
        enable = true;
        config = {
          ProgramArguments = [
            "${config.home.homeDirectory}/Applications/Home Manager Apps/${cfg.package.sourceRoot}/Contents/MacOS/Raycast"
          ];
          KeepAlive = true;
          ProcessType = "Interactive";
          StandardOutPath = "${config.xdg.cacheHome}/raycast.log";
          StandardErrorPath = "${config.xdg.cacheHome}/raycast.log";
        };
      };
    })
  ];
}
