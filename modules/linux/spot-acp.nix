# Prepared Kiro stdio boundary. Real native/TUI model-free path verified, but
# disabled until complete process custody; hooks cannot fence UserPromptSubmit.
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.spotAcp;
  sources = pkgs.runCommand "spot-acp-sources" { } ''
    mkdir -p "$out"
    cp ${./spot_acp.py} "$out/spot_acp.py"
    cp ${./spot_work.py} "$out/spot_work.py"
    cp ${./spot_frontend.py} "$out/spot_frontend.py"
  '';
  frontend = pkgs.writeShellApplication {
    name = "spot-kiro-front";
    text = ''
      exec ${pkgs.python3}/bin/python3 ${sources}/spot_frontend.py "$@"
    '';
  };
  tool = pkgs.writeShellApplication {
    name = "spot-acp-proxy";
    text = ''
      exec ${pkgs.python3}/bin/python3 ${sources}/spot_acp.py \
        --backend "''${SPOT_ACP_REAL_BACKEND:?ACP backend identity is missing}" -- "$@"
    '';
  };
  entry = pkgs.writeText "spot-kiro-entry.mjs" ''
    import { isAbsolute, join } from 'node:path';
    import { pathToFileURL } from 'node:url';
    import { installFrontend } from '${./spot-kiro-frontend.mjs}';
    const original = process.env.KIRO_CHAT_CLI_BIN;
    const proxy = '${tool}/bin/spot-acp-proxy';
    if (!original || !isAbsolute(original) || original === proxy) {
      throw new Error('Tracked Kiro backend identity unavailable; refusing an untracked fallback');
    }
    if (!process.env.HOME) throw new Error('Kiro home identity unavailable');
    process.env.SPOT_ACP_REAL_BACKEND = original;
    process.env.KIRO_CHAT_CLI_BIN = proxy;
    installFrontend('${frontend}/bin/spot-kiro-front');
    const tui = join(process.env.HOME, '.local/share/kiro-cli/tui.js');
    process.argv[1] = tui;
    await import(pathToFileURL(tui).href);
  '';
  launcher = pkgs.writeShellApplication {
    name = "spot-kiro";
    text = ''
      # The native test-entry route resolves `bun` on PATH, unlike its normal
      # bundled entry. Scope the vendor runtime to this command, not all shells.
      for arg in "$@"; do
        case "$arg" in
          --legacy-ui|--classic|--v3|--agent-engine|--agent-engine=*|--no-interactive|--non-interactive|--list-models|--list-sessions|--delete-session|--delete-session=*)
            echo 'spot-kiro requires the interactive v2 TUI; this route is not tracked' >&2
            exit 75
            ;;
        esac
      done
      runtime="''${HOME:?Kiro home identity unavailable}/.local/share/kiro-cli"
      if [[ ! -x "$runtime/bun" || ! -r "$runtime/tui.js" ]]; then
        echo 'Tracked Kiro vendor runtime unavailable; refusing fallback' >&2
        exit 75
      fi
      if ! ${config.services.spotWork.package}/bin/spot-work check-open; then
        echo 'Tracked Kiro startup admission unavailable; no backend started' >&2
        exit 75
      fi
      export PATH="$runtime:$PATH"
      export KIRO_TEST_TUI_JS_PATH=${entry}
      exec ${frontend}/bin/spot-kiro-front launch -- ${cfg.nativePackage}/bin/kiro-cli chat --tui --agent-engine v2 "$@"
    '';
  };
in
{
  options.services.spotAcp = {
    enable = lib.mkEnableOption "prepared ACP request admission (requires complete process verification)";
    nativePackage = lib.mkOption {
      type = lib.types.package;
      default = pkgs.kiro-cli;
      description = "Native Kiro package used by the explicit tracked TUI launcher";
    };
    launcherPackage = lib.mkOption {
      type = lib.types.package;
      default = launcher;
      readOnly = true;
      internal = true;
    };
    frontendPackage = lib.mkOption {
      type = lib.types.package;
      default = frontend;
      readOnly = true;
      internal = true;
    };
    entryFile = lib.mkOption {
      type = lib.types.str;
      default = toString entry;
      readOnly = true;
      internal = true;
    };
  };
  config = lib.mkIf cfg.enable {
    services.spotWork.enable = true;
    environment.systemPackages = [
      tool
      frontend
      launcher
    ];
    # Existing/native/legacy launchers stay unverified blockers. Do not impose
    # an incomplete test-entry environment on unrelated existing sessions.
  };
}
