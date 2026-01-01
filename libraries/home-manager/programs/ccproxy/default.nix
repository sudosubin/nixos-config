{
  config,
  pkgs,
  lib,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.services.ccproxy;
  toml = pkgs.formats.toml { };

in
{
  options.services.ccproxy = {
    enable = lib.mkEnableOption "ccproxy";

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.ccproxy;
      defaultText = lib.literalExpression "pkgs.ccproxy";
      description = "The ccproxy package to use.";
    };

    config = lib.mkOption {
      type = lib.types.attrsOf toml.type;
      default = { };
      description = "Configuration for ccproxy.";
      example = {
        server = {
          host = "0.0.0.0";
          port = 8000;
          log_level = "INFO";
          # log_file = "/var/log/ccproxy/ccproxy.log";
        };
        security = {
          enable_auth = false;
          # auth_token = "your-secret-token";
        };
        cors = {
          allow_origins = [ "*" ];
          allow_credentials = true;
          allow_methods = [ "*" ];
          allow_headers = [ "*" ];
        };
        claude = {
          cli_path = "auto";
          builtin_permissions = true;
          include_system_messages_in_stream = true;
        };
        scheduler = {
          enabled = true;
          max_concurrent_tasks = 10;
          graceful_shutdown_timeout = 30.0;
          default_retry_attempts = 3;
          default_retry_delay = 60.0;
        };
        logging = {
          level = "INFO";
          format = "auto";
          plugin_log_base_dir = "/tmp/ccproxy";
          enable_plugins = true;
        };
        # plugin_discovery = { };
        # plugins = { };
        docker = {
          enabled = false;
          # docker_image = "ghcr.io/anthropics/claude-code:latest";
          # docker_volumes = [ "/host/data:/container/data" ];
        };
        pricing = {
          update_interval_hours = 24;
          cache_duration_hours = 24;
          # pricing_file = "/path/to/custom/pricing.json";
        };
      };
    };
  };

  config = lib.mkMerge [
    (lib.mkIf cfg.enable {
      home.packages = [ cfg.package ];

      xdg.configFile."ccproxy/config.toml" = lib.mkIf (cfg.config != { }) {
        source = toml.generate "ccproxy-config.toml" cfg.config;
      };

      launchd.agents.ccproxy = lib.mkIf isDarwin {
        enable = true;
        config = {
          ProgramArguments = [ "${lib.getExe cfg.package}" ];
          KeepAlive = true;
          RunAtLoad = true;
          StandardOutPath = "${config.xdg.cacheHome}/ccproxy.log";
          StandardErrorPath = "${config.xdg.cacheHome}/ccproxy.log";
        };
      };
    })
  ];
}
