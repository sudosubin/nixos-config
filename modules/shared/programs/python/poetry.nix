{ config, pkgs, ... }:

{
  xdg.configFile = {
    "pypoetry/config.toml".source = ./files/poetry/config.toml;
  };
}
