{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    pipenv
    poetry
  ];

  home.sessionVariables = {
    PYTHONDONTWRITEBYTECODE = "1";
    PIPENV_VENV_IN_PROJECT = "enabled";
  };

  xdg.configFile = {
    "pip/pip.conf".source = ../files/python/pip.conf;
    "pypoetry/config.toml".source = ../files/python/config.toml;
  };
}
