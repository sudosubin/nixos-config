{
  config,
  pkgs,
  lib,
  ...
}:

{
  imports = [
    ./rofi.nix
    ./sway.nix
  ];

  home.packages = with pkgs; [
    wl-clipboard
  ];
}
