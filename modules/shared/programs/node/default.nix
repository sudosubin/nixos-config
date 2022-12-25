{ config, lib, pkgs, ... }:

{
  home.sessionVariables = {
    NEXT_TELEMETRY_DISABLED = "1";
    npm_config_cache = "${config.xdg.cacheHome}/npm";
    NPM_CONFIG_DEVDIR = "/tmp/.gyp";
    NODE_REPL_HISTORY = "${config.xdg.cacheHome}/node_repl_history";
  };
}
