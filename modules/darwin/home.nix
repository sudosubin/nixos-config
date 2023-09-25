{ config, pkgs, inputs, ... }:

{
  home-manager.useGlobalPkgs = true;
  home-manager.useUserPackages = true;
  home-manager.users."subin.kim" = { config, ... }: {
    home.username = "subin.kim";
    home.homeDirectory = "/Users/subin.kim";

    home.packages = with pkgs; [
      # Development
      curl
      hadolint
      ijhttp
      jetbrains.datagrip
      poetry
      procps
      shfmt
      sqlfluff

      # Utility
      ngrok
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
      ../shared/programs/container
      ../shared/programs/direnv
      ../shared/programs/fonts
      ../shared/programs/fzf
      ../shared/programs/git
      ../shared/programs/go
      ../shared/programs/gpg
      ../shared/programs/jq
      ../shared/programs/kubernetes
      ../shared/programs/lsd
      ../shared/programs/nix
      ../shared/programs/node
      ../shared/programs/python
      ../shared/programs/shell
      ../shared/programs/ssh
      ../shared/programs/terraform
      ../shared/programs/tmux
      ../shared/programs/vercel
      ../shared/programs/vim
      ../shared/programs/vscode
      ../shared/programs/xdg

      ../darwin/programs/caffeinate
      ../darwin/programs/cleanshot
      ../darwin/programs/clop
      ../darwin/programs/desktop
      ../darwin/programs/hammerspoon
      ../darwin/programs/homerow
      ../darwin/programs/skhd
      ../darwin/programs/yabai
    ];

    home.stateVersion = "22.05";
  };
}
