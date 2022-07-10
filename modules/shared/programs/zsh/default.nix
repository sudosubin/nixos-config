{ config, pkgs, ... }:

{
  imports = [
    ./atuin.nix
    ./zsh.nix
  ];
}
