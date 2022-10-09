{ config, pkgs, lib, ... }:
with lib;

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isLinux;
  cfg = config.services.figma-font-helper;

in
{
  options.services.figma-font-helper = {
    enable = mkEnableOption "figma-font-helper";

    port = mkOption {
      type = types.str;
      default = "18412";
      description = "Figma font helper service port.";
    };

    directories = mkOption {
      type = types.listOf types.str;
      default = [ "/usr/share/fonts" ];
      description = "Figma font helper service lookup font directories.";
    };
  };

  config = mkIf (cfg.enable && isLinux) {
    xdg.configFile = {
      "figma-linux/fonthelper".text = builtins.toJSON {
        port = cfg.port;
        directories = cfg.directories;
      };
    };

    systemd.user.services.figma-font-helper = {
      Unit = {
        Description = "Font Helper for Figma";
        After = [ "graphical-session.target" ];
      };

      Service = {
        Type = "simple";
        ExecStart = "${pkgs.figma-font-helper}/bin/fonthelper";
        Restart = "on-failure";
      };

      Install = { WantedBy = [ "default.target" ]; };
    };
  };
}
