{ pkgs, ... }:

{
  imports = [
    ./rofi.nix
    ./sway.nix
  ];

  home.packages = with pkgs; [
    wl-clipboard
  ];
}
