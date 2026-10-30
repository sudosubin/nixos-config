# Explicit NEW TUI only. Requires the exact tested PUBLIC vendor software as
# Nix inputs; no user state, runtime download, default replacement or auto app.
{ config, lib, pkgs, ... }:
let
  cfg = config.services.spotWorkShadowTui;
  files = [ "spot_work.py" "spot_shadow.py" "spot_acp.py" "spot_shadow_acp.py"
    "spot_frontend.py" "spot_shadow_frontend.py" "spot_shadow_output.py"
    "spot_shadow_ui.py" "spot-kiro-frontend.mjs" "spot-shadow-kiro-frontend.mjs"
    "spot_validation.py" "spot_shadow_tui.py" ];
  identifier = builtins.substring 0 12 (builtins.hashString "sha256"
    (lib.concatMapStrings (name: builtins.hashFile "sha256" (./. + "/${name}")) files));
  shadowID = builtins.substring 0 12 (builtins.hashString "sha256"
    (builtins.hashFile "sha256" ./spot_work.py + builtins.hashFile "sha256" ./spot_shadow.py));
  sources = pkgs.runCommand "spot-work-shadow-tui-sources" { } (''
    mkdir -p "$out"
  '' + lib.concatMapStrings (name: ''
    cp ${./. + "/${name}"} "$out/${name}"
  '') files);
  vendor = pkgs.runCommand "spot-work-shadow-tui-public-vendor" { } ''
    mkdir -p "$out"
    cp ${cfg.vendorBun} "$out/bun"
    cp ${cfg.vendorTui} "$out/tui.js"
    chmod 555 "$out/bun"
    chmod 444 "$out/tui.js"
  '';
  # Artifact generation uses the same maintained Python renderer as the warm
  # installer; expected bytes are checked again before a session can start.
  code = pkgs.runCommand "spot-work-shadow-tui-entry" { nativeBuildInputs = [ pkgs.python3 ]; } ''
    mkdir -p "$out"
    cp ${sources}/* "$out/"
    OUT="$out" VENDOR="${vendor}" PYTHON="${pkgs.python3}/bin/python3" python3 -B - <<'PY'
    import os,sys
    from pathlib import Path
    root=Path(os.environ['OUT']);sys.path.insert(0,str(root))
    import spot_shadow_tui as p
    for name,text in p.artifacts(root,os.environ['PYTHON'],os.environ['VENDOR']+'/bun',os.environ['VENDOR']+'/tui.js').items():
        (root/name).write_text(text)
        (root/name).chmod(0o444 if name.endswith('.mjs') else 0o555)
    PY
  '';
  settings = pkgs.writeText "spot-work-shadow-tui.json" (builtins.toJSON {
    schema = 1;
    deployment_id = identifier;
    shadow_deployment_id = shadowID;
    store_directory = "/var/lib/spot-work-shadow/${shadowID}";
    source_directory = "${code}";
    session_directory = "/var/lib/spot-work-shadow-tui/${identifier}/sessions";
    backend = "${cfg.nativePackage}/bin/kiro-cli-chat";
    frontend = "${cfg.nativePackage}/bin/kiro-cli";
    backend_sha256 = cfg.expectedBackendSHA;
    bun = "${vendor}/bun";
    tui = "${vendor}/tui.js";
    bun_sha256 = "67892bb6734ef352f90a964f0a2a680d5f6e6d15bdb5510e56b8065ac4d599ae";
    tui_sha256 = "67cec0aace08d9bef505ea135b908333edfb7e5ad049c3ffa678ed7bcb133384";
    fixture_only = false;
  });
  tool = pkgs.writeScriptBin "spot-work-shadow-tui" ''
    #!${pkgs.python3}/bin/python3 -I
    import sys,runpy
    sys.dont_write_bytecode = True
    sys.argv[1:1] = ["--config", "${settings}"]
    runpy.run_path("${code}/spot_shadow_tui.py", run_name="__main__")
  '';
in {
  options.services.spotWorkShadowTui = {
    enable = lib.mkEnableOption "explicit NEW TUI with independent shadow keeper; NOT full tracking";
    nativePackage = lib.mkOption { type = lib.types.package; default = pkgs.kiro-cli; };
    vendorBun = lib.mkOption { type = lib.types.nullOr lib.types.path; default = null;
      description = "Exact byte-verified PUBLIC ARM64 Bun input, never a user home/state copy"; };
    vendorTui = lib.mkOption { type = lib.types.nullOr lib.types.path; default = null;
      description = "Exact byte-verified PUBLIC Kiro2.10 TUI input, never credentials/session state"; };
    expectedBackendSHA = lib.mkOption { type = lib.types.str;
      default = "1c2a36ec26bae2bdd8d5d7cbb77606f4d072b8bc1a5cfcc6b582ae4a047ce479";
      description = "A new lock MUST be retested; never blindly refresh the native SHA"; };
  };
  config = lib.mkIf cfg.enable {
    assertions = [
      { assertion = config.services.spotWorkShadow.enable or false;
        message = "Explicit seeded disarmed shadow lineage required, never initialize canonical readiness"; }
      { assertion = cfg.vendorBun != null && cfg.vendorTui != null;
        message = "Provide the exact tested public Bun/TUI software inputs before enabling this package"; }
    ];
    environment.systemPackages = [ tool ];
    systemd.tmpfiles.rules = [ "d /var/lib/spot-work-shadow-tui 0755 root root -"
      "d /var/lib/spot-work-shadow-tui/${identifier} 0711 root root -"
      "d /var/lib/spot-work-shadow-tui/${identifier}/sessions 0711 root root -" ];
    environment.etc."spot-work-shadow-tui-current.json".text = builtins.toJSON {
      deployment_id = identifier;
      cli = "${tool}/bin/spot-work-shadow-tui";
      store_directory = "/var/lib/spot-work-shadow/${shadowID}";
      shadow_only = true;
      termination_capable = false;
      consumer_delivery_verified = false;
      work_tracking_verified = false;
    };
    # No automatic provider/model, existing launcher/environment override or
    # service stop/restart. Normal sessions have no forced runtime deadline.
  };
}
