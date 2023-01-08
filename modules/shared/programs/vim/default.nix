{ config, pkgs, lib, ... }:

{
  programs.neovim = {
    enable = true;

    viAlias = true;
    vimAlias = true;
    vimdiffAlias = true;

    withNodeJs = false;
    withRuby = false;
    withPython3 = false;

    defaultEditor = true;
    # extraConfig = "";
    # extraPackages = with pkgs; [];
    plugins = with pkgs.vimPlugins; [
      nvim-lspconfig
    ];
  };
}
