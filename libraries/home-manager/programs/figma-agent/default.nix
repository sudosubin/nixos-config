{
  config,
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin isLinux;
  cfg = config.services.figma-agent;

in
{
  options.services.figma-agent = {
    enable = lib.mkEnableOption "figma-agent";

    package = lib.mkOption {
      type = lib.types.package;
      default = if isDarwin then pkgs.figma-agent else pkgs.figma-linux-font-helper;
      defaultText = lib.literalExpression (
        if isDarwin then "pkgs.figma-agent" else "pkgs.figma-linux-font-helper"
      );
    };
  };

  config = lib.mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enable -> (isDarwin || isLinux);
          message = "services.figma-agent only supports darwin and linux.";
        }
      ];
    }

    (lib.mkIf (cfg.enable && isDarwin) {
      launchd.agents.figma-agent = {
        enable = true;
        config = {
          ProgramArguments = [ (lib.getExe cfg.package) ];
          RunAtLoad = true;
          KeepAlive = true;
          ProcessType = "Background";
          StandardOutPath = "${config.xdg.cacheHome}/figma-agent.log";
          StandardErrorPath = "${config.xdg.cacheHome}/figma-agent.log";
        };
      };
    })

    (lib.mkIf (cfg.enable && isLinux) {
      xdg.configFile."figma-linux/settings.json".text = builtins.toJSON {
        host = "127.0.0.1";
        port = "44950";
        app.fontDirs = [
          "/usr/share/fonts"
          "${config.xdg.dataHome}/fonts"
        ];
      };

      systemd.user.services.figma-agent = {
        Unit = {
          Description = "Figma Agent";
        };
        Service = {
          ExecStart = lib.getExe cfg.package;
          Restart = "on-failure";
        };
        Install = {
          WantedBy = [ "default.target" ];
        };
      };
    })
  ];
}
