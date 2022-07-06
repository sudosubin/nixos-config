{ config, pkgs, inputs, ... }:

{
  home-manager.useGlobalPkgs = true;
  home-manager.useUserPackages = true;
  home-manager.users."subin.kim" = { config, ... }: {
    home.username = "subin.kim";
    home.homeDirectory = "/Users/subin.kim";

    home.packages = with pkgs; [
      # Development
      bun
      hadolint
      jetbrains.datagrip
      kubectl
      lokalise2-cli
      minikube
      shfmt
      sqlfluff
      yarn

      # Utility
      _1password
      slack
      unzip
    ];

    secrets = {
      mount = "/tmp/user/$UID/secrets";
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
      ../shared/programs/fzf
      ../shared/programs/fonts
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

      ../darwin/programs/caffeinate
      ../darwin/programs/skhd
      ../darwin/programs/yabai
    ];

    home.stateVersion = "22.05";
  };
}
