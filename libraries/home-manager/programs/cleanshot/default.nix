{
  config,
  pkgs,
  lib,
  ...
}:
with lib;

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.services.cleanshot;

in
{
  options.services.cleanshot = {
    enable = mkEnableOption "cleanshot";

    package = mkPackageOption pkgs "cleanshot" { };
  };

  config = mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enable -> isDarwin;
          message = "Nix cleanshot only supports darwin.";
        }
      ];
    }

    (mkIf cfg.enable {
      home.packages = [ cfg.package ];

      launchd.agents.cleanshot = {
        enable = true;
        config = {
          ProgramArguments = [
            "${config.home.homeDirectory}/Applications/Home Manager Apps/${cfg.package.sourceRoot}/Contents/MacOS/CleanShot X"
          ];
          KeepAlive = true;
          ProcessType = "Interactive";
          StandardOutPath = "${config.xdg.cacheHome}/cleanshot.log";
          StandardErrorPath = "${config.xdg.cacheHome}/cleanshot.log";
        };
      };
    })
  ];
}
