{ config, lib, pkgs, ... }:

let
  inherit (pkgs) stdenv;

  colors = {
    black = "#5c6370";
    red = "#e06c75";
    green = "#98c379";
    yellow = "#e5c07b";
    blue = "#61afef";
    magenta = "#c678dd";
    cyan = "#56b6c2";
    white = "#abb2bf";
  };

  font-size = if stdenv.isDarwin then 13 else 10;
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
        decorations = if stdenv.isDarwin then "buttonless" else "full";
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
        primary.background = "#1e2127";
        primary.foreground = colors.white;
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
      };

      mouse = {
        hints.modifiers = "alt";
      };

      live_config_reload = false;
    };
  };
}
