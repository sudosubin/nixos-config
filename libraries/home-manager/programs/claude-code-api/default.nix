{
  config,
  pkgs,
  lib,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;
  cfg = config.services.claude-code-api;

  # Convert nested attrset to environment variables
  # e.g. { server = { host = "0.0.0.0"; }; } -> { CLAUDE_CODE__SERVER__HOST = "0.0.0.0"; }
  toEnvVars =
    prefix: attrs:
    lib.concatMapAttrs (
      name: value:
      let
        key = lib.toUpper "${prefix}__${name}";
      in
      if lib.isAttrs value then
        toEnvVars key value
      else if lib.isList value then
        { ${key} = builtins.toJSON value; }
      else if lib.isBool value then
        { ${key} = if value then "true" else "false"; }
      else
        { ${key} = toString value; }
    ) attrs;

in
{
  options.services.claude-code-api = {
    enable = lib.mkEnableOption "claude-code-api";

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.claude-code-api;
      defaultText = lib.literalExpression "pkgs.claude-code-api";
      description = "The claude-code-api package to use.";
    };

    config = lib.mkOption {
      type = lib.types.attrsOf lib.types.anything;
      default = { };
      description = ''
        Configuration for claude-code-api.
        Will be converted to environment variables with CLAUDE_CODE__ prefix.

        Nested attributes will be joined with double underscores.
        e.g. `{ server = { host = "0.0.0.0"; }; }` -> `{ CLAUDE_CODE__SERVER__HOST = "0.0.0.0"; }`.
      '';
      example = lib.literalExpression ''
        {
          server = {
            host = "0.0.0.0";
            port = 8080;
          };
          claude = {
            command = "claude";
            timeout_seconds = 300;
            use_interactive_sessions = false;
          };
          mcp = {
            enabled = false;
            config_file = "./mcp_config.json";
            config_json = null;
            strict = false;
            debug = false;
          };
          process_pool = {
            size = 5;
            min_idle = 2;
            max_idle = 5;
          };
        }
      '';
    };
  };

  config = lib.mkMerge [
    (lib.mkIf (cfg.enable && isDarwin) {
      launchd.agents.claude-code-api = {
        enable = true;
        config = {
          ProgramArguments = [ "${lib.getExe cfg.package}" ];
          KeepAlive = true;
          RunAtLoad = true;
          EnvironmentVariables = toEnvVars "CLAUDE_CODE" cfg.config;
          StandardOutPath = "${config.xdg.cacheHome}/claude-code-api.log";
          StandardErrorPath = "${config.xdg.cacheHome}/claude-code-api.log";
        };
      };
    })
  ];
}
