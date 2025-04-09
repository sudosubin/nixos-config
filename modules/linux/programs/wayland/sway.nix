{
  config,
  pkgs,
  lib,
  ...
}:

let
  sway = config.wayland.windowManager.sway.package;
  left = "h";
  right = "l";
  up = "k";
  down = "j";

in
{
  home.packages = with pkgs; [
    polkit_gnome
  ];

  wayland.windowManager.sway = {
    enable = true;
    wrapperFeatures.gtk = true;
    config = rec {
      modifier = "Mod4";
      terminal = "${pkgs.wezterm}/bin/wezterm";
      fonts = {
        names = [ "PragmataProMono Nerd Font Mono" ];
        style = "";
        size = 9.0;
      };
      focus = {
        followMouse = false;
      };
      colors = {
        focused = {
          border = "#58a6ff80";
          background = "#58a6ff80";
          text = "#b1bac4";
          indicator = "#58a6ff80";
          childBorder = "#58a6ff80";
        };
        focusedInactive = {
          border = "#0d1117";
          background = "#0d1117";
          text = "#b1bac4";
          indicator = "#0d1117";
          childBorder = "#0d1117";
        };
        unfocused = {
          border = "#0d1117";
          background = "#0d1117";
          text = "#b1bac4";
          indicator = "#0d1117";
          childBorder = "#0d1117";
        };
        urgent = {
          border = "#0d1117";
          background = "#ff7b72";
          text = "#b1bac4";
          indicator = "#ff7b72";
          childBorder = "#ff7b72";
        };
        placeholder = {
          border = "#0d1117";
          background = "#0d1117";
          text = "#b1bac4";
          indicator = "#0d1117";
          childBorder = "#0d1117";
        };
        background = "#ffffff";
      };
      bars = [ ];
      startup = [
        { command = "${sway}/bin/swaymsg workspace 1"; }
        { command = "${pkgs.polkit_gnome}/libexec/polkit-gnome-authentication-agent-1"; }
      ];
      keybindings = {
        # Core sway
        "${modifier}+Shift+c" = "reload";
        "${modifier}+Shift+r" = "restart";
        "${modifier}+Shift+e" = "exit";

        # Terminal
        "${modifier}+Return" = "exec ${config.wayland.windowManager.sway.config.terminal}";
        "Control+Mod1+t" = "exec ${config.wayland.windowManager.sway.config.terminal}";

        # Kill window
        "Mod1+Escape" = "kill";

        # Run rofi
        "Mod1+space" = "exec ${pkgs.rofi}/bin/rofi -show drun";

        # Focus window
        "${modifier}+${left}" = "focus left";
        "${modifier}+${down}" = "focus down";
        "${modifier}+${up}" = "focus up";
        "${modifier}+${right}" = "focus right";
        "${modifier}+space" = "focus mode_toggle";
        "${modifier}+Shift+space" = "floating toggle";

        # Move window
        "${modifier}+Shift+${left}" = "move left";
        "${modifier}+Shift+${down}" = "move down";
        "${modifier}+Shift+${up}" = "move up";
        "${modifier}+Shift+${right}" = "move right";

        # Switch workspace
        "${modifier}+1" = "workspace number 1";
        "${modifier}+2" = "workspace number 2";
        "${modifier}+3" = "workspace number 3";
        "${modifier}+4" = "workspace number 4";
        "${modifier}+5" = "workspace number 5";
        "${modifier}+6" = "workspace number 6";
        "${modifier}+7" = "workspace number 7";
        "${modifier}+8" = "workspace number 8";
        "${modifier}+9" = "workspace number 9";
        "${modifier}+0" = "workspace number 10";

        # Move to workspace
        "${modifier}+Shift+1" = "move container to workspace number 1";
        "${modifier}+Shift+2" = "move container to workspace number 2";
        "${modifier}+Shift+3" = "move container to workspace number 3";
        "${modifier}+Shift+4" = "move container to workspace number 4";
        "${modifier}+Shift+5" = "move container to workspace number 5";
        "${modifier}+Shift+6" = "move container to workspace number 6";
        "${modifier}+Shift+7" = "move container to workspace number 7";
        "${modifier}+Shift+8" = "move container to workspace number 8";
        "${modifier}+Shift+9" = "move container to workspace number 9";
        "${modifier}+Shift+0" = "move container to workspace number 10";

        # Split, Layout
        "${modifier}+b" = "splith";
        "${modifier}+v" = "splitv";
        "${modifier}+s" = "layout stacking";
        "${modifier}+w" = "layout tabbed";
        "${modifier}+e" = "layout toggle split";

        # Fullscreen
        "${modifier}+f" = "fullscreen toggle";

        # Scratchpad
        "${modifier}+Shift+minus" = "move scratchpad";
        "${modifier}+minus" = "scratchpad show";

        # Modes
        "${modifier}+r" = "mode resize";
      };
      modes = {
        resize = {
          "${left}" = "resize shrink width 10px";
          "${down}" = "resize grow height 10px";
          "${up}" = "resize shrink height 10px";
          "${right}" = "resize grow width 10px";
          "Return" = "mode default";
          "Escape" = "mode default";
        };
      };
      input."*" = {
        xkb_layout = "us";
        xkb_options = "ctrl:swapcaps,korean:ralt_hangul";
      };
    };

    extraConfig = ''
      default_border pixel 1
    '';
  };
}
