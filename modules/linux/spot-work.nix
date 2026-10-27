# Admission is on the existing EC2, not a local/paid scheduling controller.
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.spotWork;
  # No shell/PYTHONPATH/user-site hooks may run before the admission boundary.
  # The target still receives its requested environment AFTER a lease exists.
  tool = pkgs.writeScriptBin "spot-work" ''
    #!${pkgs.python3}/bin/python3 -I
    import runpy
    runpy.run_path("${./spot_work.py}", run_name="__main__")
  '';
in
{
  options.services.spotWork = {
    enable = lib.mkEnableOption "atomic job admission and manual shutdown extensions";
    package = lib.mkOption {
      type = lib.types.package;
      default = tool;
      readOnly = true;
      internal = true;
    };
  };
  config = lib.mkIf cfg.enable {
    environment.systemPackages = [ tool ];
    systemd.tmpfiles.rules = [
      "d /run/spot-schedule-guard 0755 root root -"
      "d /run/spot-schedule-guard/leases 1733 root root -"
      "d /run/spot-schedule-guard/participants 1733 root root -"
      "f /run/spot-schedule-guard/admission.lock 0660 root users -"
    ];
    # Jobs already starting before the fence remain visible as systemd jobs;
    # jobs starting afterwards fail the condition without doing maintenance.
    systemd.services =
      (lib.genAttrs [ "nix-gc" "nix-optimise" "docker-prune" ] (_: {
        requires = [ "spot-work-admission-ready.service" ];
        after = [ "spot-work-admission-ready.service" ];
        serviceConfig.ExecCondition = "${tool}/bin/spot-work check-open";
      }))
      // {
        spot-work-admission-ready = {
          description = "Initialize root-owned work admission before schedule guards";
          wantedBy = [ "multi-user.target" ];
          before = [
            "spot-scale-in-protection-ready.service"
            "spot-schedule-guard.service"
          ];
          serviceConfig = {
            Type = "oneshot";
            RemainAfterExit = true;
            ExecStart = "${tool}/bin/spot-work initialize";
            UMask = "0077";
          };
        };
      };
  };
}
