{
  config,
  lib,
  pkgs,
  ...
}:

{
  imports = [
    ./kubectl.nix
  ];

  home.packages = with pkgs; [
    k3d
  ];
}
