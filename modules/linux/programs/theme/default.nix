{ config, pkgs, ... }:

{
  gtk = {
    enable = true;

    theme = {
      package = pkgs.arc-theme;
      name = "Arc-Light";
    };

    iconTheme = {
      package = pkgs.la-capitaine-icon-theme;
      name = "la-capitaine-icon-theme";
    };

    gtk2.configLocation = "${config.xdg.configHome}/gtk-2.0/gtkrc";
    gtk3.extraConfig = {
      "gtk-application-prefer-dark-theme" = true;
    };
    gtk4.extraConfig = {
      "gtk-application-prefer-dark-theme" = true;
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
