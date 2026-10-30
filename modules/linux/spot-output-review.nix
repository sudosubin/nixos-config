# Explicit read-only OUTPUT recovery only; no backend input/session takeover.
{ config, lib, pkgs, ... }:
let
  cfg = config.services.spotOutputReview;
  files = [ "spot_work.py" "spot_shadow.py" "spot_acp.py" "spot_shadow_acp.py"
    "spot_validation.py" "spot_shadow_review.py" ];
  identifier = builtins.substring 0 12 (builtins.hashString "sha256"
    (lib.concatMapStrings (name: builtins.hashFile "sha256" (./. + "/${name}")) files));
  shadowID = builtins.substring 0 12 (builtins.hashString "sha256"
    (builtins.hashFile "sha256" ./spot_work.py + builtins.hashFile "sha256" ./spot_shadow.py));
  code = pkgs.runCommand "spot-output-review-source" { } (''
    mkdir -p "$out"
  '' + lib.concatMapStrings (name: ''
    cp ${./. + "/${name}"} "$out/${name}"
  '') files);
  tool = pkgs.writeScriptBin "spot-output-review" ''
    #!${pkgs.python3}/bin/python3 -I
    import sys,runpy
    sys.dont_write_bytecode = True
    sys.argv[1:1] = ["--expected-version", "${identifier}", "--store", "/var/lib/spot-work-shadow/${shadowID}"]
    runpy.run_path("${code}/spot_shadow_review.py", run_name="__main__")
  '';
in {
  options.services.spotOutputReview.enable = lib.mkEnableOption "explicit leased OUTPUT review, NOT delivery/idle authority";
  config = lib.mkIf cfg.enable {
    assertions = [{ assertion = config.services.spotWorkShadow.enable or false;
      message = "Existing shadow lineage required; review never initializes canonical or work state"; }];
    environment.systemPackages = [ tool ];
    environment.etc."spot-output-review-current.json".text = builtins.toJSON {
      deployment_id = identifier;
      cli = "${tool}/bin/spot-output-review";
      store_directory = "/var/lib/spot-work-shadow/${shadowID}";
      readonly_output_only = true;
      consumer_delivery_verified = false;
      work_tracking_verified = false;
      termination_capable = false;
    };
  };
}
