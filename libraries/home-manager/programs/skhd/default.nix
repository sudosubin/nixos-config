{ config, pkgs, lib, ... }:
with lib;

let
  inherit (pkgs) stdenv;
  cfg = config.services.skhd;

in
{
  options.services.skhd = {
    enable = mkEnableOption "skhd";

    package = mkOption {
      type = types.package;
      default = pkgs.skhd;
      description = "A skhd package.";
    };

    config = mkOption {
      type = types.lines;
      default = "";
      example = "alt + shift - r   :   chunkc quit";
      description = "Config to use for <filename>skhdrc</filename>.";
    };
  };

  config = mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enable -> stdenv.isDarwin;
          message = "Nix skhd only supports darwin.";
        }
      ];
    }

    (mkIf cfg.enable {
      xdg.configFile = {
        "skhd/skhdrc".text = cfg.config;
      };

      launchd.agents.skhd = {
        enable = true;
        config = {
          ProgramArguments =
            [ "${cfg.package}/bin/skhd" ]
            ++ optionals (cfg.config != "") [ "-c" "${config.xdg.configHome}/skhd/skhdrc" ];
          KeepAlive = true;
          ProcessType = "Interactive";
          StandardOutPath = "${config.xdg.cacheHome}/skhd.log";
          StandardErrorPath = "${config.xdg.cacheHome}/skhd.log";
        };
      };
    })
  ];
}
