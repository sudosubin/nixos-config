{ config, pkgs, ... }:

{
  home.username = "sudosubin";
  home.homeDirectory = "/home/sudosubin";

  home.packages = with pkgs; [
    # Development
    act
    hadolint
    kubectl
    ll
    lokalise2-cli
    minikube
    pipenv
    poetry
    yarn

    # Utility
    gnome.nautilus
    google-chrome
    pavucontrol
    pulseaudio
    slack
    xdg-utils
  ];

  imports = [
    ./programs/alacritty.nix
    ./programs/awscli.nix
    ./programs/bat.nix
    ./programs/bpython.nix
    ./programs/docker.nix
    ./programs/fonts.nix
    ./programs/fzf.nix
    ./programs/gh.nix
    ./programs/git.nix
    ./programs/gpg.nix
    ./programs/input-method.nix
    ./programs/pass.nix
    ./programs/ssh.nix
    ./programs/xorg.nix
    ./programs/zpl-open.nix
    ./programs/zsh.nix
  ];
}
