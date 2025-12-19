{
  config,
  pkgs,
  inputs,
  ...
}:

{
  home-manager.useGlobalPkgs = true;
  home-manager.useUserPackages = true;
  home-manager.users.sudosubin =
    { config, ... }:
    {
      home.username = "sudosubin";
      home.homeDirectory = "/home/sudosubin";

      home.packages = with pkgs; [
        # Development
        curl
        hadolint
        ijhttp
        jetbrains.datagrip
        jetbrains.idea
        shfmt

        # Utility
        figma-linux
        gnome.nautilus
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
        inputs.nixos-config-private-karrot.homeManagerModules.karrot
        inputs.nixos-config-private-sudosubin.homeManagerModules.sudosubin

        ../shared/programs/1password
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
        ../shared/programs/helix
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
        ../shared/programs/vscode
        ../shared/programs/xdg
        ../shared/programs/zed-editor

        ../linux/programs/input-method
        ../linux/programs/theme
        ../linux/programs/wayland
        ../linux/programs/zpl-open
      ];

      home.stateVersion = "25.05";
    };
}
