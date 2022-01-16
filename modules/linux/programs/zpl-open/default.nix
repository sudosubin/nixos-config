{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    zpl-open
  ];

  xdg.mimeApps = {
    enable = true;
    defaultApplications = {
      "x-scheme-handler/zpl" = [ "zpl-opener.desktop" ];
    };
  };
}
