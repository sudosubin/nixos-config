{ config, pkgs, ... }:

{
  home.username = "sudosubin";
  home.homeDirectory = "/home/sudosubin";

  imports = [
    ./programs/git.nix
    ./programs/wayland.nix
  ];
}
