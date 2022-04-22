{ config, lib, pkgs, ... }:

let
  mod = "alt";
  left = "h";
  right = "l";
  up = "k";
  down = "j";

in
{
  services.skhd = {
    enable = true;

    config = builtins.concatStringsSep "\n" [
      # Core skhd
      "${mod} + shift - r : ${pkgs.skhd}/bin/skhd --reload"

      # Terminal
      "${mod} - return : open -na Alacritty.app"
      "ctrl + cmd - t : open -na Alacritty.app"

      # Kill window
      "${mod} - w : yabai -m window --close"

      # Focus window
      "${mod} - ${left} : yabai -m window --focus west"
      "${mod} - ${down} : yabai -m window --focus south"
      "${mod} - ${up} : yabai -m window --focus north"
      "${mod} - ${right} : yabai -m window --focus east"
      "${mod} + shift - space : yabai -m window --toggle float && yabai -m window --grid 4:4:1:1:2:2"

      # Move window
      "${mod} + shift - ${left} : yabai -m window --swap west"
      "${mod} + shift - ${down} : yabai -m window --swap south"
      "${mod} + shift - ${up} : yabai -m window --swap north"
      "${mod} + shift - ${right} : yabai -m window --swap east"

      # Switch workspace
      "${mod} - 1 : yabai -m space --focus 1"
      "${mod} - 2 : yabai -m space --focus 2"
      "${mod} - 3 : yabai -m space --focus 3"
      "${mod} - 4 : yabai -m space --focus 4"
      "${mod} - 5 : yabai -m space --focus 5"
      "${mod} - 6 : yabai -m space --focus 6"
      "${mod} - 7 : yabai -m space --focus 7"
      "${mod} - 8 : yabai -m space --focus 8"
      "${mod} - 9 : yabai -m space --focus 9"
      "${mod} - 0 : yabai -m space --focus 10"

      # Move to workspace
      "${mod} + shift - 1 : yabai -m window --space 1"
      "${mod} + shift - 2 : yabai -m window --space 2"
      "${mod} + shift - 3 : yabai -m window --space 3"
      "${mod} + shift - 4 : yabai -m window --space 4"
      "${mod} + shift - 5 : yabai -m window --space 5"
      "${mod} + shift - 6 : yabai -m window --space 6"
      "${mod} + shift - 7 : yabai -m window --space 7"
      "${mod} + shift - 8 : yabai -m window --space 8"
      "${mod} + shift - 9 : yabai -m window --space 9"
      "${mod} + shift - 0 : yabai -m window --space 10"

      # Split, Layout
      "${mod} - b : yabai -m window --insert south"
      "${mod} - v : yabai -m window --insert east"
      "${mod} - e : yabai -m window --toggle split"

      # Fullscreen
      "${mod} - f : yabai -m window --toggle zoom-fullscreen"
    ];
  };
}
