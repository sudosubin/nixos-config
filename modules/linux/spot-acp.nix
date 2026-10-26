# Prepared Kiro stdio boundary. Disabled until the native launcher and complete
# process coverage are verified; hook exit codes cannot fence UserPromptSubmit.
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
  '';
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
    const original = process.env.KIRO_CHAT_CLI_BIN;
    const proxy = '${tool}/bin/spot-acp-proxy';
    if (!original || !isAbsolute(original) || original === proxy) {
      throw new Error('Tracked Kiro backend identity unavailable; refusing an untracked fallback');
    }
    if (!process.env.HOME) throw new Error('Kiro home identity unavailable');
    process.env.SPOT_ACP_REAL_BACKEND = original;
    process.env.KIRO_CHAT_CLI_BIN = proxy;
    const tui = join(process.env.HOME, '.local/share/kiro-cli/tui.js');
    process.argv[1] = tui;
    await import(pathToFileURL(tui).href);
  '';
in
{
  options.services.spotAcp.enable = lib.mkEnableOption "prepared ACP request admission (requires native launcher verification)";
  config = lib.mkIf cfg.enable {
    services.spotWork.enable = true;
    environment.systemPackages = [ tool ];
    environment.sessionVariables.KIRO_TEST_TUI_JS_PATH = toString entry;
  };
}
