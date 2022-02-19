{ config, pkgs, inputs, ... }:

{
  nixpkgs.config.allowUnfree = true;
  home-manager.useGlobalPkgs = true;
  home-manager.useUserPackages = true;
  home-manager.users."subin.kim" = { config, lib, pkgs, ... }: {
    home.username = "subin.kim";
    home.homeDirectory = "/Users/subin.kim";

    home.activation = {
      copyApplications =
        let
          apps = pkgs.buildEnv {
            name = "home-manager-applications";
            paths = config.home.packages;
            pathsToLink = "/Applications";
          };
        in
        lib.hm.dag.entryAfter [ "writeBoundary" ] ''
          baseDir="$HOME/Applications/Home Manager Apps"
          if [ -d "$baseDir" ]; then
            rm -rf "$baseDir"
          fi
          mkdir -p "$baseDir"
          for appFile in ${apps}/Applications/*; do
            target="$baseDir/$(basename "$appFile")"
            $DRY_RUN_CMD cp ''${VERBOSE_ARG:+-v} -fHRL "$appFile" "$baseDir"
            $DRY_RUN_CMD chmod ''${VERBOSE_ARG:+-v} -R +w "$target"
          done
        '';
    };

    home.packages = with pkgs; [
      # Development
      hadolint

      # Utility
      slack
    ];

    secrets = {
      identityPaths = [ "${config.home.homeDirectory}/.ssh/id_ed25519" ];
    };

    imports = [
      ../shared/programs/act
      ../shared/programs/alacritty
      ../shared/programs/aws
      ../shared/programs/bat
      ../shared/programs/docker
      ../shared/programs/fzf
      ../shared/programs/fonts
      ../shared/programs/git
      ../shared/programs/gpg
      ../shared/programs/himalaya
      ../shared/programs/lsd
      ../shared/programs/nix
      ../shared/programs/password-store
      ../shared/programs/python
      ../shared/programs/ssh
      ../shared/programs/tmux
      ../shared/programs/vscode
      ../shared/programs/zsh
    ];
  };
}
