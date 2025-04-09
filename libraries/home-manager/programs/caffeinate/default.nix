{
  config,
  pkgs,
  lib,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.services.caffeinate;

in
{
  options.services.caffeinate = {
    enable = lib.mkEnableOption "caffeinate";

    path = lib.mkOption {
      type = lib.types.str;
      default = "/usr/bin/caffeinate";
      description = "Caffeinate bin location.";
    };

    args = lib.mkOption {
      type = lib.types.str;
      default = "";
      description = "Caffeinate execute command arguments.";
    };
  };

  config = lib.mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enable -> isDarwin;
          message = "Nix caffeinate only supports darwin.";
        }
      ];
    }

    (lib.mkIf cfg.enable {
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
