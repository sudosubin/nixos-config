{
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin isLinux;
  toLua = lib.generators.toLua { };
  colors = import ../../colors.nix;

  font =
    if isLinux then
      [
        { family = "PragmataProMono Nerd Font Mono"; }
      ]
    else
      [
        { family = "PragmataProMono Nerd Font Mono"; }
        {
          family = "Apple Color Emoji";
          assume_emoji_presentation = true;
        }
      ];
  font-size = if isDarwin then 13 else 10;

in
{
  programs.wezterm = {
    enable = true;

    extraConfig = ''
      return ${
        toLua {
          automatically_reload_config = true;
          color_scheme = "default";
          enable_scroll_bar = true;
          font = lib.generators.mkLuaInline ''
            wezterm.font_with_fallback(${toLua font})
          '';
          font_size = font-size;
          front_end = "WebGpu";
          hide_tab_bar_if_only_one_tab = true;
          keys = [
            {
              key = "Enter";
              mods = "SHIFT";
              action = lib.generators.mkLuaInline "wezterm.action.SendString '\\n'";
            }
          ];
          scrollback_lines = 100000;
          window_decorations = "RESIZE";
        }
      };
    '';

    colorSchemes = {
      default = {
        foreground = colors.ansi.white;
        background = colors.background;

        cursor_bg = colors.ansi.white;
        cursor_fg = colors.ansi.black;
        cursor_border = colors.ansi.white;

        selection_fg = "none";
        selection_bg = "rgba(255, 255, 255, 5%)";

        # scrollbar_thumb = "";

        # split = "";

        ansi = [
          colors.ansi.black
          colors.ansi.red
          colors.ansi.green
          colors.ansi.yellow
          colors.ansi.blue
          colors.ansi.magenta
          colors.ansi.cyan
          colors.ansi.white
        ];
        brights = [
          colors.brights.black
          colors.brights.red
          colors.brights.green
          colors.brights.yellow
          colors.brights.blue
          colors.brights.magenta
          colors.brights.cyan
          colors.brights.white
        ];
        compose_cursor = colors.ansi.green;
      };
    };

    enableBashIntegration = true;
    enableZshIntegration = false;
  };
}
