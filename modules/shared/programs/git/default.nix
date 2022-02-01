{ config, pkgs, ... }:

{
  imports = [
    ./delta.nix
    ./gh.nix
    ./git.nix
  ];
}
