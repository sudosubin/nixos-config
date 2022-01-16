{ config, pkgs, ... }:

{
  xdg.configFile = {
    "bpython/config".source = ./bpython/config;
    "bpython/base16.theme".source = ./bpython/base16.theme;
  };
}
