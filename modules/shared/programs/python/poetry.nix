{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    poetry
  ];

  xdg.configFile = {
    "pypoetry/config.toml".source = ./files/poetry/config.toml;
  };
}
