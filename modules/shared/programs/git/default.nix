{ config, pkgs, ... }:

{
  imports = [
    ./delta.nix
    ./gh.nix
    ./git.nix
  ];

  home.packages = with pkgs; [ git-spr ];
}
