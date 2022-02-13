{ config, lib, pkgs, ... }:

{
  home.packages = with pkgs; [
    lsd
  ];

  programs.lsd = {
    enable = true;
    settings = {
      color.theme = "custom";
      date = "+%e %b %H:%M";
      symlink-arrow = "";
    };
  };

  xdg.configFile."lsd/themes/custom.yaml" = {
    source = (pkgs.formats.yaml { }).generate "lsd-theme" {
      user = "dark_grey";
      group = "dark_grey";
      permission = {
        read = "dark_green";
        write = "dark_yellow";
        exec = "dark_red";
        exec-sticky = "dark_magenta";
        no-access = "dark_grey";
      };
      date = {
        hour-old = "white";
        day-old = "white";
        older = "dark_grey";
      };
      size = {
        none = "dark_grey";
        small = "dark_green";
        medium = "dark_yellow";
        large = "dark_red";
      };
    };
  };
}
