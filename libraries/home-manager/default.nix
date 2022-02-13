{ config, pkgs, inputs, ... }:

{
  home-manager.sharedModules = [
    # home-manager-secrets (nix flake input)
    inputs.home-manager-secrets.homeManagerModules.home-manager-secrets

    # local programs (local)
    ./programs/act
    ./programs/lsd
  ];
}
