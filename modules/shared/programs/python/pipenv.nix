{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    pipenv
  ];

  home.sessionVariables = {
    PIPENV_VENV_IN_PROJECT = "enabled";
  };
}
