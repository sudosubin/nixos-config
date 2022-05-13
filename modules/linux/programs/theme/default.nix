{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    apple-cursor-theme
    arc-theme
    la-capitaine-icon-theme
  ];

  gtk = {
    enable = true;
    theme.name = "Arc-Dark";
    iconTheme.name = "la-capitaine-icon-theme";
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
