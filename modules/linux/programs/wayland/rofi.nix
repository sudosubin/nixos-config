{ config, pkgs, lib, ... }:

{
  home.packages = with pkgs; [
    rofi
  ];

  programs.rofi = {
    enable = true;
    font = "mono 12";
    terminal = "${pkgs.alacritty}/bin/alacritty";
    cycle = true;
    theme = "Arc-Dark";
    extraConfig = {
      modi = "window,run";
    };
  };
}
