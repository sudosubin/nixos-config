{ config, pkgs, lib, ... }:

{
  programs.rofi = {
    enable = true;
    font = "mono 12";
    terminal = "${pkgs.wezterm}/bin/wezterm";
    cycle = true;
    theme = "Arc-Dark";
    extraConfig = {
      modi = "window,run";
    };
  };
}
