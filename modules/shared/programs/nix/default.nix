{ pkgs, lib, config, ... }:

{
  home.sessionVariables = {
    NIX_ACTIVATE_ROOT = "${config.home.homeDirectory}/Code/github.com/sudosubin/nixos-flakes";
  };

  home.packages = with pkgs; [
    nil
    nixVersions.nix_2_26
    nixpkgs-fmt
    nix-activate
  ];
}
