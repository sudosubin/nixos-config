{ config, pkgs, ... }:

{
  imports = [
    ./zsh.nix
  ];

  home.file = {
    ".hushlogin".text = "";
  };
}
