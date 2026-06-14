{ ... }:

{
  services.yabai = {
    enable = true;
    enableScriptingAddition = true;

    config = {
      # Global Settings
      mouse_follows_focus = "on";
      window_origin_display = "focused";
      window_shadow = "float";
      auto_balance = "on";
      mouse_modifier = "ctrl";

      # Space Settings
      layout = "bsp";
      window_gap = "4";
      window_placement = "second_child";
    };

    extraConfig = ''
      # First-party
      yabai -m rule --add app="^System Settings$" manage="off"

      # Third-party
      yabai -m rule --add app="^CleanShot X$" manage="off"
      yabai -m rule --add app="^1Password$" title="^Quick Access — 1Password$" manage="off"
      yabai -m rule --add app="^Slack$" space="1"
    '';
  };
}
