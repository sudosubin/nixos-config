{ config, pkgs, ... }:

{
  home.username = "sudosubin";
  home.homeDirectory = "/home/sudosubin";

  imports = [
    ./programs/alacritty.nix
    ./programs/git.nix
    ./programs/wayland.nix
  ];
}
