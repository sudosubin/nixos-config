{ config, pkgs, ... }:

{
  home.username = "sudosubin";
  home.homeDirectory = "/home/sudosubin";

  home.packages = with pkgs; [
    act
    google-chrome
    hadolint
    kubectl
    ll
    lokalise2-cli
    minikube
    pipenv
    poetry
    slack
    xdg-utils
    yarn
  ];

  imports = [
    ./programs/alacritty.nix
    ./programs/awscli.nix
    ./programs/bat.nix
    ./programs/docker.nix
    ./programs/fonts.nix
    ./programs/fzf.nix
    ./programs/gh.nix
    ./programs/git.nix
    ./programs/gpg.nix
    ./programs/input-method.nix
    ./programs/pass.nix
    ./programs/ssh.nix
    ./programs/wayland.nix
    ./programs/zpl-open.nix
    ./programs/zsh.nix
  ];
}
