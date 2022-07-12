{ config, pkgs, ... }:

{
  home.sessionVariables = {
    PIPENV_VENV_IN_PROJECT = "enabled";
  };
}
