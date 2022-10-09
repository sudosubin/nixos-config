{ config, pkgs, lib, ... }:
with lib;

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.services.yabai;

  hasYabaiConfig = (cfg.config != { } || cfg.extraConfig != "");

  toYabaiConfig = config:
    concatStringsSep "\n" (mapAttrsToList
      (p: v: "yabai -m config ${p} ${toString v}")
      config);

in
{
  options.services.yabai = {
    enable = mkEnableOption "yabai";

    package = mkPackageOption pkgs "yabai" { };

    config = mkOption {
      type = types.attrs;
      default = { };
      example = literalExpression ''
        {
          layout = "bsp";
          window_placement = "first_child";
          top_padding = 20;
        }
      '';
      description = "Yabai configuration attrs.";
    };

    extraConfig = mkOption {
      type = types.str;
      default = "";
      example = literalExpression ''
        yabai -m rule --add app="^System Preferences$" manage=off
      '';
      description = "Extra yabai configurations.";
    };
  };

  config = mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enable -> isDarwin;
          message = "Nix yabai only supports darwin.";
        }
      ];
    }

    (mkIf cfg.enable {
      home.packages = [ cfg.package ];

      xdg.configFile = mkIf hasYabaiConfig
        {
          "yabai/yabairc" = {
            text = "${toYabaiConfig cfg.config}"
              + optionalString (cfg.extraConfig != "") ("\n" + cfg.extraConfig + "\n");
            executable = true;
          };
        };

      launchd.agents.yabai = {
        enable = true;
        config = {
          ProgramArguments = [ "${cfg.package}/bin/yabai" ]
            ++ optionals (hasYabaiConfig) [ "-c" "${config.xdg.configHome}/yabai/yabairc" ];
          KeepAlive = true;
          RunAtLoad = true;
          EnvironmentVariables = {
            PATH = builtins.concatStringsSep ":" ([
              "/run/current-system/sw/bin"
              "${cfg.package}/bin"
              "${config.home.profileDirectory}/bin"
            ]);
          };
          StandardOutPath = "${config.xdg.cacheHome}/yabai.log";
          StandardErrorPath = "${config.xdg.cacheHome}/yabai.log";
        };
      };
    })
  ];
}
