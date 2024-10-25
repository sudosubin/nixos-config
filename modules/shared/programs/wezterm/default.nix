{ config, lib, pkgs, ... }:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;

  colors = {
    black = "#5c6370";
    red = "#e06c75";
    green = "#98c379";
    yellow = "#e5c07b";
    blue = "#61afef";
    magenta = "#c678dd";
    cyan = "#56b6c2";
    white = "#abb2bf";
    background = "#1e2127";
  };

  font-size = if isDarwin then 13 else 10;
  font-family = "PragmataProMono Nerd Font Mono";

in
{
  programs.wezterm = {
    enable = true;

    extraConfig = ''
      return {
        automatically_reload_config = true,
        color_scheme = 'default',
        font = wezterm.font('${font-family}'),
        font_size = 13,
        front_end = 'WebGpu',
        hide_tab_bar_if_only_one_tab = true,
        window_decorations = 'RESIZE',
      }
    '';

    colorSchemes = {
      default = {
        foreground = colors.white;
        background = colors.background;

        cursor_bg = colors.white;
        cursor_fg = colors.background;
        cursor_border = colors.white;

        selection_fg = "none";
        selection_bg = "rgba(255, 255, 255, 5%)";

        # scrollbar_thumb = "";

        # split = "";

        ansi = [
          colors.black
          colors.red
          colors.green
          colors.yellow
          colors.blue
          colors.magenta
          colors.cyan
          colors.white
        ];
        brights = [
          colors.black
          colors.red
          colors.green
          colors.yellow
          colors.blue
          colors.magenta
          colors.cyan
          colors.white
        ];
        compose_cursor = colors.green;
      };
    };

    enableBashIntegration = true;
    enableZshIntegration = false;
  };
}
