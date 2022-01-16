{ config, pkgs, ... }:

{
  nixpkgs.config.allowUnfree = true;
  nixpkgs.overlays = [
    (import ../shared/overlays/ll.nix)
    (import ../shared/overlays/pipenv.nix)
    (import ../shared/overlays/pretendard.nix)
    (import ../shared/overlays/vscode.nix)

    (import ../linux/overlays/apple-cursor-theme.nix)
    (import ../linux/overlays/google-chrome.nix)
    (import ../linux/overlays/zpl-open.nix)
  ];

  home-manager.useGlobalPkgs = true;
  home-manager.useUserPackages = true;
  home-manager.users.sudosubin = {
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
      ../shared/programs/alacritty
      ../shared/programs/aws
      ../shared/programs/bat
      ../shared/programs/docker
      ../shared/programs/fzf
      ../shared/programs/git
      ../shared/programs/gpg
      ../shared/programs/password-store
      ../shared/programs/python
      ../shared/programs/ssh
      ../shared/programs/tmux
      ../shared/programs/vscode
      ../shared/programs/zsh

      ../linux/programs/fonts
      ../linux/programs/input-method
      ../linux/programs/theme
      ../linux/programs/wayland
      ../linux/programs/zpl-open
    ];
  };
}
