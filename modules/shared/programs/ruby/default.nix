{ config, ... }:

{
  home.sessionVariables = {
    BUNDLE_USER_CACHE = "${config.xdg.cacheHome}/bundle";
    BUNDLE_USER_CONFIG = "${config.xdg.configHome}/bundle/config";
    GEM_SPEC_CACHE = "${config.xdg.cacheHome}/gem/specs";
  };
}
