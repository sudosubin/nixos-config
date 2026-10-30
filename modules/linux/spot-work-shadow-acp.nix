# Explicit NEW ACP keeper only. No TUI replacement, ready/idle or automatic app.
{ config, lib, pkgs, ... }:
let
  cfg = config.services.spotWorkShadowAcp;
  shadowID = builtins.substring 0 12 (builtins.hashString "sha256" (
    builtins.hashFile "sha256" ./spot_work.py + builtins.hashFile "sha256" ./spot_shadow.py
  ));
  identifier = builtins.substring 0 12 (builtins.hashString "sha256" (
    builtins.hashFile "sha256" ./spot_work.py + builtins.hashFile "sha256" ./spot_shadow.py
    + builtins.hashFile "sha256" ./spot_acp.py + builtins.hashFile "sha256" ./spot_shadow_acp.py
  ));
  sources = pkgs.runCommand "spot-work-shadow-acp-sources" { } ''
    mkdir -p "$out"
    cp ${./spot_work.py} "$out/spot_work.py"
    cp ${./spot_shadow.py} "$out/spot_shadow.py"
    cp ${./spot_acp.py} "$out/spot_acp.py"
    cp ${./spot_shadow_acp.py} "$out/spot_shadow_acp.py"
  '';
  settings = pkgs.writeText "spot-work-shadow-acp.json" (builtins.toJSON {
    schema = 1;
    deployment_id = identifier;
    shadow_deployment_id = shadowID;
    store_directory = "/var/lib/spot-work-shadow/${shadowID}";
    backend = "${cfg.nativePackage}/bin/kiro-cli-chat";
    backend_sha256 = cfg.expectedBackendSHA;
  });
  tool = pkgs.writeScriptBin "spot-work-shadow-acp" ''
    #!${pkgs.python3}/bin/python3 -I
    import sys,runpy
    sys.dont_write_bytecode = True
    sys.argv[1:1] = ["--config", "${settings}"]
    runpy.run_path("${sources}/spot_shadow_acp.py", run_name="__main__")
  '';
in {
  options.services.spotWorkShadowAcp = {
    enable = lib.mkEnableOption "explicit new shadow ACP keeper, NOT full work tracking";
    nativePackage = lib.mkOption { type = lib.types.package; default = pkgs.kiro-cli; };
    expectedBackendSHA = lib.mkOption {
      type = lib.types.str;
      default = "1c2a36ec26bae2bdd8d5d7cbb77606f4d072b8bc1a5cfcc6b582ae4a047ce479";
      description = "Actual tested Kiro2.10 native bytes. A new lock MUST be retested; never blindly refresh this SHA.";
    };
  };
  config = lib.mkIf cfg.enable {
    assertions = [{ assertion = config.services.spotWorkShadow.enable or false;
      message = "ACP keeper requires explicitly seeded disarmed shadow custody, never canonical startup initialization"; }];
    environment.systemPackages = [ tool ];
    environment.etc."spot-work-shadow-acp-current.json".text = builtins.toJSON {
      deployment_id = identifier;
      cli = "${tool}/bin/spot-work-shadow-acp";
      store_directory = "/var/lib/spot-work-shadow/${shadowID}";
      shadow_only = true;
      termination_capable = false;
      consumer_delivery_verified = false;
    };
    # No automatic provider session, new credentials, TUI/home activation or
    # restart of any existing Kiro/Herdr/user/Docker/SSM service on activation.
  };
}
