{ config, pkgs, ... }:

{
  home.username = "sudosubin";
  home.homeDirectory = "/home/sudosubin";

  imports = [
    ./programs/alacritty.nix
    ./programs/awscli.nix
    ./programs/fonts.nix
    ./programs/git.nix
    ./programs/wayland.nix
  ];
}
