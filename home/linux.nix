{ config, pkgs, ... }:

{
  home.username = "sudosubin";
  home.homeDirectory = "/home/sudosubin";

  imports = [
    ./programs/alacritty.nix
    ./programs/awscli.nix
    ./programs/docker.nix
    ./programs/fonts.nix
    ./programs/gh.nix
    ./programs/git.nix
    ./programs/google-chrome.nix
    ./programs/gpg.nix
    ./programs/pass.nix
    ./programs/ssh.nix
    ./programs/wayland.nix
  ];
}
