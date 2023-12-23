{ config, pkgs, inputs, ... }:

{
  home-manager.useGlobalPkgs = true;
  home-manager.useUserPackages = true;
  home-manager.users.sudosubin = { config, ... }: {
    home.username = "sudosubin";
    home.homeDirectory = "/home/sudosubin";

    home.packages = with pkgs; [
      # Development
      curl
      hadolint
      ijhttp
      jetbrains.datagrip
      poetry
      shfmt
      sqlfluff

      # Utility
      figma-linux
      gnome.nautilus
      google-chrome
      ngrok
      pavucontrol
      pulseaudio
      ripgrep
      slack
      unzip
      xdg-utils
    ];

    secrets = {
      identityPaths = [ "${config.home.homeDirectory}/.ssh/id_ed25519" ];
      enableForceReload = true;
    };

    imports = [
      inputs.nixos-config-private-sudosubin.homeManagerModules.sudosubin
      inputs.nixos-config-private-toss.homeManagerModules.toss

      ../shared/programs/1password
      ../shared/programs/act
      ../shared/programs/alacritty
      ../shared/programs/aws
      ../shared/programs/bat
      ../shared/programs/container
      ../shared/programs/direnv
      ../shared/programs/fonts
      ../shared/programs/git
      ../shared/programs/go
      ../shared/programs/gpg
      ../shared/programs/jq
      ../shared/programs/kubernetes
      ../shared/programs/lsd
      ../shared/programs/nix
      ../shared/programs/node
      ../shared/programs/python
      ../shared/programs/rust
      ../shared/programs/shell
      ../shared/programs/ssh
      ../shared/programs/terraform
      ../shared/programs/tmux
      ../shared/programs/vercel
      ../shared/programs/vim
      ../shared/programs/vscode
      ../shared/programs/xdg

      ../linux/programs/input-method
      ../linux/programs/theme
      ../linux/programs/wayland
      ../linux/programs/zpl-open
    ];

    home.stateVersion = "22.05";
  };
}
