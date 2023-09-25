{ config, lib, pkgs, ... }:

let
  mod = "alt";
  left = "h";
  right = "l";
  up = "k";
  down = "j";

  bins = {
    skhd = "${pkgs.skhd}/bin/skhd";
    yabai = "${pkgs.yabai}/bin/yabai";
  };

in
{
  services.skhd = {
    enable = true;

    config = builtins.concatStringsSep "\n" [
      # Core skhd
      "${mod} + shift - r : ${bins.skhd} --reload"

      # Terminal
      "${mod} - return : open -na Alacritty.app"
      "ctrl + cmd - t : open -na Alacritty.app"

      # Kill window
      "${mod} - w : ${bins.yabai} -m window --close"

      # Focus window
      "${mod} - ${left} : ${bins.yabai} -m window --focus west"
      "${mod} - ${down} : ${bins.yabai} -m window --focus south"
      "${mod} - ${up} : ${bins.yabai} -m window --focus north"
      "${mod} - ${right} : ${bins.yabai} -m window --focus east"
      "${mod} + shift - space : ${bins.yabai} -m window --toggle float && yabai -m window --grid 4:4:1:1:2:2"

      # Move window
      "${mod} + shift - ${left} : ${bins.yabai} -m window --swap west"
      "${mod} + shift - ${down} : ${bins.yabai} -m window --swap south"
      "${mod} + shift - ${up} : ${bins.yabai} -m window --swap north"
      "${mod} + shift - ${right} : ${bins.yabai} -m window --swap east"

      # Switch workspace
      "${mod} - 1 : ${bins.yabai} -m space --focus 1"
      "${mod} - 2 : ${bins.yabai} -m space --focus 2"
      "${mod} - 3 : ${bins.yabai} -m space --focus 3"
      "${mod} - 4 : ${bins.yabai} -m space --focus 4"
      "${mod} - 5 : ${bins.yabai} -m space --focus 5"
      "${mod} - 6 : ${bins.yabai} -m space --focus 6"
      "${mod} - 7 : ${bins.yabai} -m space --focus 7"
      "${mod} - 8 : ${bins.yabai} -m space --focus 8"
      "${mod} - 9 : ${bins.yabai} -m space --focus 9"
      "${mod} - 0 : ${bins.yabai} -m space --focus 10"

      # Move to workspace
      "${mod} + shift - 1 : ${bins.yabai} -m window --space 1"
      "${mod} + shift - 2 : ${bins.yabai} -m window --space 2"
      "${mod} + shift - 3 : ${bins.yabai} -m window --space 3"
      "${mod} + shift - 4 : ${bins.yabai} -m window --space 4"
      "${mod} + shift - 5 : ${bins.yabai} -m window --space 5"
      "${mod} + shift - 6 : ${bins.yabai} -m window --space 6"
      "${mod} + shift - 7 : ${bins.yabai} -m window --space 7"
      "${mod} + shift - 8 : ${bins.yabai} -m window --space 8"
      "${mod} + shift - 9 : ${bins.yabai} -m window --space 9"
      "${mod} + shift - 0 : ${bins.yabai} -m window --space 10"

      # Split, Layout
      "${mod} - b : ${bins.yabai} -m window --insert south"
      "${mod} - v : ${bins.yabai} -m window --insert east"
      "${mod} - e : ${bins.yabai} -m window --toggle split"

      # Fullscreen
      "${mod} - f : ${bins.yabai} -m window --toggle zoom-fullscreen"
    ];
  };
}
