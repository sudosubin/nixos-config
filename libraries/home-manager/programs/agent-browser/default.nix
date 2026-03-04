{
  config,
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin isLinux;
  cfg = config.programs.agent-browser;

  xdgRuntimeDirCommand =
    if isLinux then
      ''export XDG_RUNTIME_DIR="/run/user/$UID"''
    else if isDarwin then
      ''export XDG_RUNTIME_DIR="$(getconf DARWIN_USER_TEMP_DIR)"''
    else
      null;

  shouldWrapXdgRuntimeDir = cfg.enableXdgRuntimeDir && xdgRuntimeDirCommand != null;

  package =
    if shouldWrapXdgRuntimeDir || cfg.enableNativeMode then
      pkgs.agent-browser.overrideAttrs (oldAttrs: {
        nativeBuildInputs = (oldAttrs.nativeBuildInputs or [ ]) ++ [ pkgs.makeWrapper ];

        postInstall = ''
          ${oldAttrs.postInstall or ""}
          wrapProgram $out/bin/agent-browser \
            ${lib.concatStringsSep " \\\n  " (
              (lib.optional cfg.enableNativeMode "--set AGENT_BROWSER_NATIVE 1")
              ++ (lib.optional shouldWrapXdgRuntimeDir "--run '${xdgRuntimeDirCommand}'")
            )}
        '';
      })
    else
      pkgs.agent-browser;

in
{
  options.programs.agent-browser = {
    enable = lib.mkEnableOption "agent-browser";

    enableNativeMode = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = ''
        Set AGENT_BROWSER_NATIVE=1 at runtime when launching agent-browser.
      '';
    };

    enableXdgRuntimeDir = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = ''
        Set XDG_RUNTIME_DIR at runtime when launching agent-browser.
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
          message = "programs.agent-browser.enableXdgRuntimeDir only supports Linux and Darwin.";
        }
      ];
    }

    (lib.mkIf cfg.enable {
      home.packages = [ package ];
    })
  ];
}
