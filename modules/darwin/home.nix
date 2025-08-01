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
        google-cloud-sdk
        hadolint
        ijhttp
        jetbrains.datagrip
        jetbrains.idea-ultimate
        ngrok
        postman
        procps
        shfmt

        # Utility
        cleanshot
        deskpad
        nodePackages.localtunnel
        redisinsight
        ripgrep
        unzip
      ];

      secrets = {
        mount = "/tmp/user/$UID/secrets";
        identityPaths = [ "${config.home.homeDirectory}/.ssh/id_ed25519" ];
        enableForceReload = true;
      };

      imports = [
        inputs.nixvim.homeManagerModules.nixvim
        inputs.nixos-config-private-daangn.homeManagerModules.daangn
        inputs.nixos-config-private-sudosubin.homeManagerModules.sudosubin

        # ../shared/programs/1password
        ../shared/programs/act
        ../shared/programs/aws
        ../shared/programs/bat
        ../shared/programs/claude-code
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
        ../shared/programs/terraform
        ../shared/programs/vim
        ../shared/programs/vscode
        ../shared/programs/wezterm
        ../shared/programs/xdg

        ../darwin/programs/caffeinate
        ../darwin/programs/cleanshot
        ../darwin/programs/clop
        ../darwin/programs/desktop
        ../darwin/programs/hammerspoon
        ../darwin/programs/homerow
        ../darwin/programs/raycast
        ../darwin/programs/yabai
      ];

      home.stateVersion = "25.05";
    };
}
