{ config, pkgs, ... }:

{
  imports = [
    ./programs/git.nix
  ];

  # home.packages = with pkgs; [
  #   git
  # ];
}
