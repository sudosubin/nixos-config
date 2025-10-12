{
  config,
  pkgs,
  lib,
  ...
}:

{
  programs.rofi = {
    enable = true;
    font = "mono 12";
    terminal = lib.getExe pkgs.wezterm;
    cycle = true;
    theme = "Arc-Dark";
    extraConfig = {
      modi = "window,run";
    };
  };
}
