{ config, lib, pkgs, ... }:

{
  imports = [
    ./k9s.nix
    ./kubectl.nix
  ];

  home.packages = with pkgs; [
    k3d
  ];
}
