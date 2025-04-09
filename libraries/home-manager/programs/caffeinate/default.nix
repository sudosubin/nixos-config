{
  config,
  pkgs,
  lib,
  ...
}:
with lib;

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.services.caffeinate;

in
{
  options.services.caffeinate = {
    enable = mkEnableOption "caffeinate";

    path = mkOption {
      type = types.str;
      default = "/usr/bin/caffeinate";
      description = "Caffeinate bin location.";
    };

    args = mkOption {
      type = types.str;
      default = "";
      description = "Caffeinate execute command arguments.";
    };
  };

  config = mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enable -> isDarwin;
          message = "Nix caffeinate only supports darwin.";
        }
      ];
    }

    (mkIf cfg.enable {
      launchd.agents.caffeinate = {
        enable = true;
        config = {
          ProgramArguments = [
            cfg.path
            cfg.args
          ];
          KeepAlive = true;
          RunAtLoad = true;
        };
      };
    })
  ];
}
