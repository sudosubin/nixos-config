{ config, pkgs, lib, ... }:
with lib;

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.services.shottr;

in
{
  options.services.shottr = {
    enable = mkEnableOption "shottr";

    package = mkPackageOption pkgs "shottr" { };
  };

  config = mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enable -> isDarwin;
          message = "Nix shottr only supports darwin.";
        }
      ];
    }

    (mkIf cfg.enable {
      home.packages = [ cfg.package ];

      launchd.agents.shottr = {
        enable = true;
        config = {
          ProgramArguments = [ "${config.home.homeDirectory}/Applications/Home Manager Apps/${cfg.package.sourceRoot}/Contents/MacOS/Shottr" ];
          KeepAlive = true;
          ProcessType = "Interactive";
          StandardOutPath = "${config.xdg.cacheHome}/shottr.log";
          StandardErrorPath = "${config.xdg.cacheHome}/shottr.log";
        };
      };
    })
  ];
}
