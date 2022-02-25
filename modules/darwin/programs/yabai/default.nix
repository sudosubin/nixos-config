{ config, lib, pkgs, ... }:

{
  services.yabai = {
    enable = true;
    enableScriptingAddition = true;

    package = pkgs.yabai;

    config = {
      layout = "bsp";
      window_shadow = "float";

      window_placement = "second_child";
    };

    extraConfig = ''
    '';
  };
}
