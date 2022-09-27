{ config, pkgs, lib, ... }:

{
  programs.neovim = {
    enable = true;

    withNodeJs = false;
    withRuby = false;
    withPython3 = false;
  };
}
