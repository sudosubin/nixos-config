{ config, lib, pkgs, ... }:

{
  services.yabai = {
    enable = true;

    config = {
      layout = "bsp";
      window_shadow = "float";
      window_placement = "second_child";
    };

    extraConfig = ''
    '';
  };
}
