# Prepared lifecycle adapter. No external scheduler or live application restart.
{
  config,
  lib,
  ...
}:
let
  cfg = config.services.spotGateway;
in
{
  options.services.spotGateway = {
    enable = lib.mkEnableOption "verified non-forcing OpenClaw lifecycle adapter";
    unit = lib.mkOption {
      type = lib.types.strMatching "[a-zA-Z0-9@_.-]+\\.service";
      default = "openclaw-kiro-discord.service";
    };
    vendorDirectory = lib.mkOption {
      type = lib.types.str;
      default = "/home/sudosubin/.local/share/openclaw-npm/lib/node_modules/openclaw/dist";
    };
    node = lib.mkOption {
      type = lib.types.str;
      # The installed OpenClaw rejects base Node 24.12's SQLite TEXT/NUL bug.
      # This supported runtime is already persisted alongside the app on home.
      default = "/home/sudosubin/.local/share/openclaw-npm/node-v26.4.0-linux-arm64/bin/node";
    };
  };
  config = lib.mkIf cfg.enable {
    services.spotWork.enable = true;
    # Drop-ins augment the actual HM-owned unit; do not replace its ExecStart,
    # credentials, restart policy or configuration. Root owns the admission CLI.
    systemd.user.services.${lib.removeSuffix ".service" cfg.unit} = {
      overrideStrategy = "asDropin";
      serviceConfig = {
        ExecCondition = "${config.services.spotWork.package}/bin/spot-work check-service-open ${cfg.unit}";
        TimeoutStopSec = "infinity";
        SendSIGKILL = false;
      };
    };
  };
}
