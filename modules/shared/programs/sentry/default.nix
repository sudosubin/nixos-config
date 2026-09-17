{ config, pkgs, ... }:

{
  home.packages = [ pkgs.sentry ];

  home.sessionVariables = {
    SENTRY_CONFIG_DIR = "${config.xdg.configHome}/sentry";
  };
}
