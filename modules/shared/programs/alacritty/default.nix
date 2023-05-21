{ config, lib, pkgs, ... }:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;

  colors = {
    black = "#24292f";
    red = "#cf222e";
    green = "#1a7f37";
    yellow = "#9a6700";
    blue = "#0969da";
    magenta = "#8250df";
    cyan = "#3192aa";
    white = "#6e7781";
  };

  font-size = if isDarwin then 13 else 10;
  font-family = "PragmataProMono Nerd Font Mono";

in
{
  programs.alacritty = {
    enable = true;
    settings = {
      env = {
        TERM = "screen-256color";
      };

      window = {
        dimensions = {
          columns = 96;
          lines = 24;
        };
        padding = {
          x = 8;
          y = 6;
        };
        dynamic_padding = true;
        title = "Terminal";
        dynamic_title = true;
        decorations = if isDarwin then "buttonless" else "full";
      };

      scrolling = {
        history = 10000;
        multiplier = 1;
      };

      font = {
        size = font-size;
        normal.family = font-family;
        bold.family = font-family;
        italic.family = font-family;
        bold_italic.family = font-family;
      };

      colors = {
        primary.background = "#ffffff";
        primary.foreground = "#0E1116";
        normal.black = colors.black;
        normal.red = colors.red;
        normal.green = colors.green;
        normal.yellow = colors.yellow;
        normal.blue = colors.blue;
        normal.magenta = colors.magenta;
        normal.cyan = colors.cyan;
        normal.white = colors.white;
        bright.black = colors.black;
        bright.red = colors.red;
        bright.green = colors.green;
        bright.yellow = colors.yellow;
        bright.blue = colors.blue;
        bright.magenta = colors.magenta;
        bright.cyan = colors.cyan;
        bright.white = colors.white;
        indexed_colors = [
          { index = 16; color = "#d18616"; }
          { index = 17; color = "#a40e26"; }
        ];
      };

      mouse = {
        hints.modifiers = "alt";
      };

      live_config_reload = false;
    };
  };
}
