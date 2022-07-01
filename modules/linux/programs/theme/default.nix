{ config, pkgs, ... }:

{
  gtk = {
    enable = true;

    theme = {
      package = pkgs.arc-theme;
      name = "Arc-Dark";
    };

    iconTheme = {
      package = pkgs.la-capitaine-icon-theme;
      name = "la-capitaine-icon-theme";
    };
  };

  gtk.gtk2 = {
    configLocation = "${config.xdg.configHome}/gtk-2.0/gtkrc";
  };

  gtk.gtk3 = {
    extraConfig = {
      "gtk-application-prefer-dark-theme" = 1;
    };
  };

  home.pointerCursor = {
    package = pkgs.apple-cursor-theme;
    name = "apple-cursor-theme";
    size = 22;

    x11.enable = true;
    gtk.enable = true;
  };
}
