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
      default = pkgs.figma-agent;
      defaultText = lib.literalExpression "pkgs.figma-agent";
    };
  };

  config = lib.mkIf cfg.enable (
    lib.mkMerge [
      {
        assertions = [
          {
            assertion = isDarwin || isLinux;
            message = "services.figma-agent only supports darwin and linux.";
          }
        ];

        xdg.configFile."figma-agent/config.json".text = builtins.toJSON {
          host = "127.0.0.1";
          port = 44950;
          tls_port = null;
        };
      }

      (lib.mkIf isDarwin {
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

      (lib.mkIf isLinux {
        systemd.user.services.figma-agent = {
          Unit.Description = "Figma Agent";
          Service = {
            ExecStart = lib.getExe cfg.package;
            Restart = "on-failure";
          };
          Install.WantedBy = [ "default.target" ];
        };
      })
    ]
  );
}
