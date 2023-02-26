{ config, pkgs, lib, ... }:
with lib;

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.services.clop;

in
{
  options.services.clop = {
    enable = mkEnableOption "clop";

    package = mkPackageOption pkgs "clop" { };
  };

  config = mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enable -> isDarwin;
          message = "Nix clop only supports darwin.";
        }
      ];
    }

    (mkIf cfg.enable {
      home.packages = [ cfg.package ];

      launchd.agents.clop = {
        enable = true;
        config = {
          ProgramArguments =
            [ "${config.home.homeDirectory}/Applications/Home Manager Apps/${cfg.package.sourceRoot}/Contents/MacOS/Clop" ];
          KeepAlive = true;
          ProcessType = "Interactive";
          StandardOutPath = "${config.xdg.cacheHome}/clop.log";
          StandardErrorPath = "${config.xdg.cacheHome}/clop.log";
        };
      };
    })
  ];
}
