{ config, pkgs, ... }:

{
  home.sessionVariables = {
    PYTHONDONTWRITEBYTECODE = "1";
  };

  xdg.configFile = {
    "pip/pip.conf".source = ./python/pip.conf;
  };
}
