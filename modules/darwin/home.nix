{ config, pkgs, inputs, ... }:

{
  home-manager.useGlobalPkgs = true;
  home-manager.useUserPackages = true;
  home-manager.users."subin.kim" = { config, ... }: {
    home.username = "subin.kim";
    home.homeDirectory = "/Users/subin.kim";

    home.packages = with pkgs; [
      # Development
      hadolint
      jetbrains.datagrip
      jetbrains.idea-community
      kubectl
      poetry
      procps
      servicex
      shfmt
      sqlfluff

      # Utility
      cleanshot
      discord
      ngrok
      raycast
      redisinsight
      ripgrep
      slack
      unzip
      zoom-us
    ];

    secrets = {
      mount = "/tmp/user/$UID/secrets";
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
      ../shared/programs/direnv
      ../shared/programs/docker
      ../shared/programs/fzf
      ../shared/programs/fonts
      ../shared/programs/git
      ../shared/programs/go
      ../shared/programs/gpg
      ../shared/programs/himalaya
      ../shared/programs/jq
      ../shared/programs/lsd
      ../shared/programs/nix
      ../shared/programs/node
      ../shared/programs/python
      ../shared/programs/ssh
      ../shared/programs/terraform
      ../shared/programs/tmux
      ../shared/programs/vim
      ../shared/programs/vscode
      ../shared/programs/xdg
      ../shared/programs/zsh

      ../darwin/programs/caffeinate
      ../darwin/programs/desktop
      ../darwin/programs/skhd
      ../darwin/programs/yabai
    ];

    home.stateVersion = "22.05";
  };
}
