{
  config,
  pkgs,
  inputs,
  ...
}:

{
  home-manager.useGlobalPkgs = true;
  home-manager.useUserPackages = true;
  home-manager.users.elvin =
    { config, ... }:
    {
      home.username = "elvin";
      home.homeDirectory = "/Users/elvin";

      home.packages = with pkgs; [
        # Development
        curl
        cursor-cli
        devbox
        google-cloud-sdk
        hadolint
        ijhttp
        jetbrains.datagrip
        jetbrains.idea
        ngrok
        postman
        procps
        shfmt

        # Utility
        cleanshot
        deskpad
        grandperspective
        nodePackages.localtunnel
        redisinsight
        ripgrep
        unzip
      ];

      secrets = {
        mount = "${config.xdg.cacheHome}/home-manager-secrets";
        identityPaths = [ "${config.home.homeDirectory}/.ssh/id_ed25519" ];
        enableForceReload = true;
      };

      imports = [
        inputs.nixvim.homeModules.nixvim
        inputs.nixos-config-private-karrot.homeManagerModules.karrot
        inputs.nixos-config-private-sudosubin.homeManagerModules.sudosubin

        # ../shared/programs/1password
        ../shared/programs/act
        ../shared/programs/ai
        ../shared/programs/aws
        ../shared/programs/bat
        ../shared/programs/container
        ../shared/programs/direnv
        ../shared/programs/firefox
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
        ../shared/programs/terminal
        ../shared/programs/terraform
        ../shared/programs/tmux
        ../shared/programs/vim
        ../shared/programs/vscode
        ../shared/programs/xdg

        ../darwin/programs/caffeinate
        ../darwin/programs/cleanshot
        ../darwin/programs/clop
        ../darwin/programs/desktop
        ../darwin/programs/hammerspoon
        ../darwin/programs/homerow
        ../darwin/programs/yabai
      ];

      home.stateVersion = "25.05";
    };
}
