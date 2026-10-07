{
  config,
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.services.cleanshot;

in
{
  options.services.cleanshot = {
    enable = lib.mkEnableOption "cleanshot";

    package = lib.mkPackageOption pkgs "cleanshot" { };
  };

  config = lib.mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enable -> isDarwin;
          message = "Nix cleanshot only supports darwin.";
        }
        {
          assertion = cfg.enable -> config.targets.darwin.copyApps.enable;
          message = "services.cleanshot requires targets.darwin.copyApps.enable.";
        }
      ];
    }

    (lib.mkIf cfg.enable {
      home.packages = [ cfg.package ];

      launchd.agents.cleanshot = {
        enable = true;
        config = {
          ProgramArguments = [
            "${config.home.homeDirectory}/${config.targets.darwin.copyApps.directory}/CleanShot X.app/Contents/MacOS/CleanShot X"
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
