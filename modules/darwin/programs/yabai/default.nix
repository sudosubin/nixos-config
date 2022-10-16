{ config, lib, pkgs, ... }:

{
  services.yabai = {
    enable = true;

    config = {
      # Global Settings
      mouse_follows_focus = "on";
      window_origin_display = "focused";
      window_topmost = "on";
      window_shadow = "float";
      auto_balance = "on";
      mouse_modifier = "ctrl";

      # Space Settings
      layout = "bsp";
      window_placement = "second_child";
    };

    extraConfig = ''
      yabai -m rule --add app="^System Preferences$" manage="off"
    '';
  };
}
