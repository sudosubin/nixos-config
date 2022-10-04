{ config, pkgs, ... }:

{
  imports = [
    ./atuin.nix
    ./zsh.nix
  ];

  home.file = {
    ".hushlogin".text = "";
  };
}
