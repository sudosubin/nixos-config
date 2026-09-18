{
  config,
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin isLinux;
  cfg = config.programs.agent-slack;

  xdgRuntimeDirCommand =
    if isLinux then
      ''export XDG_RUNTIME_DIR="/run/user/$UID"''
    else if isDarwin then
      ''export XDG_RUNTIME_DIR="$(getconf DARWIN_USER_TEMP_DIR)"''
    else
      null;

  shouldWrapXdgRuntimeDir = cfg.enableXdgRuntimeDir && xdgRuntimeDirCommand != null;

  package =
    if shouldWrapXdgRuntimeDir then
      pkgs.agent-slack.overrideAttrs (oldAttrs: {
        nativeBuildInputs = (oldAttrs.nativeBuildInputs or [ ]) ++ [ pkgs.makeWrapper ];

        postInstall = ''
          ${oldAttrs.postInstall or ""}
          wrapProgram $out/bin/agent-slack \
            --run '${xdgRuntimeDirCommand}'
        '';
      })
    else
      pkgs.agent-slack;

in
{
  options.programs.agent-slack = {
    enable = lib.mkEnableOption "agent-slack";

    enableXdgRuntimeDir = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = ''
        Set XDG_RUNTIME_DIR at runtime when launching agent-slack.
        Linux: /run/user/$UID
        Darwin: $(getconf DARWIN_USER_TEMP_DIR)
      '';
    };
  };

  config = lib.mkMerge [
    {
      assertions = [
        {
          assertion = cfg.enableXdgRuntimeDir -> (isLinux || isDarwin);
          message = "programs.agent-slack.enableXdgRuntimeDir only supports Linux and Darwin.";
        }
      ];
    }

    (lib.mkIf cfg.enable {
      home.packages = [ package ];
    })
  ];
}
