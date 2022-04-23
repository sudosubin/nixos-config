{ config, pkgs, lib, inputs, ... }:

let
  inherit (pkgs) stdenv;

in
{
  home-manager.sharedModules = [
    # home-manager-secrets (nix flake input)
    inputs.home-manager-secrets.homeManagerModules.home-manager-secrets

    # local programs (local)
    ./programs/act
    ./programs/figma-font-helper
    ./programs/jq
    ./programs/lsd
    ./programs/skhd
    ./programs/yabai

    # os systems
    (lib.mkIf (stdenv.isLinux) ./systems/linux)
    (lib.mkIf (stdenv.isDarwin) ./systems/darwin)
  ];
}
