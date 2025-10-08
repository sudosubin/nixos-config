{
  config,
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;

  colors = {
    background = "#0d1117";
    ansi = {
      black = "#484f58";
      white = "#b1bac4";
      red = "#ff7b72";
      green = "#3fb950";
      yellow = "#d29922";
      blue = "#58a6ff";
      magenta = "#bc8cff";
      cyan = "#39c5cf";
    };
    brights = {
      black = "#6e7681";
      white = "#ffffff";
      red = "#ffa198";
      green = "#56d364";
      yellow = "#e3b341";
      blue = "#79c0ff";
      magenta = "#d2a8ff";
      cyan = "#56d4dd";
    };
  };

  font-size = if isDarwin then 13 else 10;
  font-family = "PragmataProMono Nerd Font Mono";

in
{
  home.sessionVariables = {
    COLORFGBG = "1;15";
  };

  programs.alacritty = {
    enable = true;
    settings = {
      colors = {
        primary.background = colors.background;
        primary.foreground = colors.ansi.white;
        normal.black = colors.ansi.black;
        normal.red = colors.ansi.red;
        normal.green = colors.ansi.green;
        normal.yellow = colors.ansi.yellow;
        normal.blue = colors.ansi.blue;
        normal.magenta = colors.ansi.magenta;
        normal.cyan = colors.ansi.cyan;
        normal.white = colors.ansi.white;
        bright.black = colors.brights.black;
        bright.red = colors.brights.red;
        bright.green = colors.brights.green;
        bright.yellow = colors.brights.yellow;
        bright.blue = colors.brights.blue;
        bright.magenta = colors.brights.magenta;
        bright.cyan = colors.brights.cyan;
        bright.white = colors.brights.white;
      };

      env = {
        TERM = "screen-256color";
      };

      font = {
        size = font-size;
        normal.family = font-family;
        bold.family = font-family;
        italic.family = font-family;
        bold_italic.family = font-family;
      };

      general.live_config_reload = false;

      keyboard.bindings = [
        {
          key = "Return";
          mods = "Shift";
          chars = "\n";
        }
      ];

      scrolling = {
        history = 10000;
        multiplier = 1;
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
    };
  };
}
