{ config, pkgs, inputs, ... }:

{
  home-manager.useGlobalPkgs = true;
  home-manager.useUserPackages = true;
  home-manager.users.sudosubin = { config, ... }: {
    home.username = "sudosubin";
    home.homeDirectory = "/home/sudosubin";

    home.packages = with pkgs; [
      # Development
      go-task
      hadolint
      jetbrains.datagrip
      kubectl
      lokalise2-cli
      minikube
      shfmt
      sqlfluff
      yarn

      # Utility
      gnome.nautilus
      google-chrome
      pavucontrol
      pulseaudio
      slack
      xdg-utils
    ];

    secrets = {
      identityPaths = [ "${config.home.homeDirectory}/.ssh/id_ed25519" ];
      enableForceReload = true;
    };

    imports = [
      inputs.nixos-config-private-sudosubin.homeManagerModules.sudosubin
      inputs.nixos-config-private-toss.homeManagerModules.toss

      ../shared/programs/act
      ../shared/programs/alacritty
      ../shared/programs/aws
      ../shared/programs/bat
      ../shared/programs/direnv
      ../shared/programs/docker
      ../shared/programs/fonts
      ../shared/programs/fzf
      ../shared/programs/git
      ../shared/programs/gpg
      ../shared/programs/himalaya
      ../shared/programs/jq
      ../shared/programs/lsd
      ../shared/programs/nix
      ../shared/programs/password-store
      ../shared/programs/python
      ../shared/programs/ssh
      ../shared/programs/tmux
      ../shared/programs/vscode
      ../shared/programs/zsh

      ../linux/programs/figma-font-helper
      ../linux/programs/input-method
      ../linux/programs/theme
      ../linux/programs/wayland
      ../linux/programs/zpl-open
    ];
  };
}
