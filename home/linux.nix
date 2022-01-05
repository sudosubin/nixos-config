{ config, pkgs, ... }:

{
  home.username = "sudosubin";
  home.homeDirectory = "/home/sudosubin";

  home.packages = with pkgs; [
    google-chrome
    slack
  ];

  imports = [
    ./programs/alacritty.nix
    ./programs/awscli.nix
    ./programs/docker.nix
    ./programs/fonts.nix
    ./programs/gh.nix
    ./programs/git.nix
    ./programs/gpg.nix
    ./programs/pass.nix
    ./programs/ssh.nix
    ./programs/wayland.nix
  ];
}
