{
  config,
  pkgs,
  lib,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.services.yabai;

  hasYabaiConfig = (cfg.config != { } || cfg.extraConfig != "");

  toYabaiConfig =
    config:
    lib.concatStringsSep "\n" (lib.mapAttrsToList (p: v: "yabai -m config ${p} ${toString v}") config);

in
{
  options.services.yabai = {
    enable = lib.mkEnableOption "yabai";

    package = lib.mkPackageOption pkgs "yabai" { };

    config = lib.mkOption {
      type = lib.types.attrs;
      default = { };
      example = lib.literalExpression ''
        {
          layout = "bsp";
          window_placement = "first_child";
          top_padding = 20;
        }
      '';
      description = "Yabai configuration attrs.";
    };

    extraConfig = lib.mkOption {
      type = lib.types.str;
      default = "";
      example = lib.literalExpression ''
        yabai -m rule --add app="^System Preferences$" manage=off
      '';
      description = "Extra yabai configurations.";
    };
  };

  config = lib.mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enable -> isDarwin;
          message = "Nix yabai only supports darwin.";
        }
      ];
    }

    (lib.mkIf cfg.enable {
      home.packages = [ cfg.package ];

      xdg.configFile = lib.mkIf hasYabaiConfig {
        "yabai/yabairc" = {
          text =
            "${toYabaiConfig cfg.config}"
            + lib.optionalString (cfg.extraConfig != "") ("\n" + cfg.extraConfig + "\n");
          executable = true;
        };
      };

      launchd.agents.yabai = {
        enable = true;
        config = {
          ProgramArguments = [
            "${cfg.package}/bin/yabai"
          ]
          ++ lib.optionals (hasYabaiConfig) [
            "-c"
            "${config.xdg.configHome}/yabai/yabairc"
          ];
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
