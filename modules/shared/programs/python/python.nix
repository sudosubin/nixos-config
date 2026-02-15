{ config, ... }:

{
  home.sessionVariables = {
    IPYTHONDIR = "${config.xdg.configHome}/ipython";
    PYTHONDONTWRITEBYTECODE = "1";
    PYTHONSTARTUP = "${config.xdg.configHome}/python/startup.py";
    RYE_HOME = "${config.xdg.configHome}/rye";
  };

  xdg.configFile = {
    "python/startup.py".source = ./files/python/startup.py;
  };
}
