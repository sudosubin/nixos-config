{
  config,
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.programs.wifi-unredactor;

in
{
  options.programs.wifi-unredactor = {
    enable = lib.mkEnableOption "wifi-unredactor";

    package = lib.mkPackageOption pkgs "wifi-unredactor" { };
  };

  config = lib.mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enable -> isDarwin;
          message = "Nix wifi-unredactor only supports darwin.";
        }
        {
          assertion = cfg.enable -> config.targets.darwin.copyApps.enable;
          message = "programs.wifi-unredactor requires targets.darwin.copyApps.enable (for Location Services authorization).";
        }
      ];
    }

    (lib.mkIf cfg.enable {
      # locationd binds to the bundle path, so the CLI execs the copyApps copy
      home.packages = [
        cfg.package
        (pkgs.writeShellScriptBin "wifi-unredactor" ''
          exec "${config.home.homeDirectory}/${config.targets.darwin.copyApps.directory}/WiFi Unredactor.app/Contents/MacOS/wifi-unredactor" "$@"
        '')
      ];
    })
  ];
}
