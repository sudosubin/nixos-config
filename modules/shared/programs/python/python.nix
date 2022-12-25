{ config, pkgs, ... }:

{
  home.sessionVariables = {
    IPYTHONDIR = "${config.xdg.configHome}/ipython";
    PYTHONDONTWRITEBYTECODE = "1";
    # PYTHONSTARTUP = ./files/python/startup.py;
  };

  xdg.configFile = {
    "pip/pip.conf".source = ./files/python/pip.conf;
  };
}
