{ config, pkgs, lib, ... }:

let
  mod = config.xsession.windowManager.i3.config.modifier;
  left = "h";
  right = "l";
  up = "k";
  down = "j";

in {
  home.packages = with pkgs; [
    i3
    rofi
  ];

  xsession = {
    enable = true;
  };

  xsession.windowManager.i3 = {
    enable = true;
    config = {
      modifier = "Mod4";
      terminal = "${pkgs.alacritty}/bin/alacritty";
      fonts = {
        names = [ "FiraMono Nerd Font Mono" ];
        style = "";
        size = 9.0;
      };
      focus = {
        followMouse = false;
      };
      colors = {
        focused = { border = "#61AFEF80"; background = "#61AFEF80"; text = "#ABB2BF"; indicator = "#61AFEF80"; childBorder = "#61AFEF80"; };
        focusedInactive = { border = "#1E2127"; background = "#1E2127"; text = "#ABB2BF"; indicator = "#1E2127"; childBorder = "#1E2127"; };
        unfocused = { border = "#1E2127"; background = "#1E2127"; text = "#ABB2BF"; indicator = "#1E2127"; childBorder = "#1E2127"; };
        urgent = { border = "#1E2127"; background = "#E06C75"; text = "#ABB2BF"; indicator = "#E06C75"; childBorder = "#E06C75"; };
        placeholder = { border = "#1E2127"; background = "#1E2127"; text = "#ABB2BF"; indicator = "#1E2127"; childBorder = "#1E2127"; };
        background = "#FFFFFF";
      };
      keybindings = {
        # Core i3
        "${mod}+Shift+c" = "reload";
        "${mod}+Shift+r" = "restart";
        "${mod}+Shift+e" = "exit";

        # Terminal
        "${mod}+Return" = "exec ${config.xsession.windowManager.i3.config.terminal}";
        "Control+Mod1+t" = "exec ${config.xsession.windowManager.i3.config.terminal}";

        # Kill window
        "Mod1+Escape" = "kill";

        # Run rofi
        "Mod1+space" = "exec ${pkgs.rofi}/bin/rofi -show drun";

        # Focus window
        "${mod}+${left}" = "focus left";
        "${mod}+${down}" = "focus down";
        "${mod}+${up}" = "focus up";
        "${mod}+${right}" = "focus right";
        "${mod}+space" = "focus mode_toggle";
        "${mod}+Shift+space" = "floating toggle";

        # Move window
        "${mod}+Shift+${left}" = "move left";
        "${mod}+Shift+${down}" = "move down";
        "${mod}+Shift+${up}" = "move up";
        "${mod}+Shift+${right}" = "move right";

        # Switch workspace
        "${mod}+1" = "workspace number 1";
        "${mod}+2" = "workspace number 2";
        "${mod}+3" = "workspace number 3";
        "${mod}+4" = "workspace number 4";
        "${mod}+5" = "workspace number 5";
        "${mod}+6" = "workspace number 6";
        "${mod}+7" = "workspace number 7";
        "${mod}+8" = "workspace number 8";
        "${mod}+9" = "workspace number 9";
        "${mod}+0" = "workspace number 10";

        # Move to workspace
        "${mod}+Shift+1" = "move container to workspace number 1";
        "${mod}+Shift+2" = "move container to workspace number 2";
        "${mod}+Shift+3" = "move container to workspace number 3";
        "${mod}+Shift+4" = "move container to workspace number 4";
        "${mod}+Shift+5" = "move container to workspace number 5";
        "${mod}+Shift+6" = "move container to workspace number 6";
        "${mod}+Shift+7" = "move container to workspace number 7";
        "${mod}+Shift+8" = "move container to workspace number 8";
        "${mod}+Shift+9" = "move container to workspace number 9";
        "${mod}+Shift+10" = "move container to workspace number 10";

        # Split, Layout
        "${mod}+b" = "splith";
        "${mod}+v" = "splitv";
        "${mod}+s" = "layout stacking";
        "${mod}+w" = "layout tabbed";
        "${mod}+e" = "layout toggle split";

        # Fullscreen
        "${mod}+f" = "fullscreen toggle";

        # Scratchpad
        "${mod}+Shift+minus" = "move scratchpad";
        "${mod}+minus" = "scratchpad show";
      };
    };

    extraConfig = ''
      default_border pixel 1
    '';
  };

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

