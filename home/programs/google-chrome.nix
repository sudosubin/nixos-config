{ config, pkgs, lib, ... }:

{
  home.packages = with pkgs; [
    google-chrome
  ];

#  home.packages = with pkgs; [
#    google-chrome.overrideAttrs (old: {
#      commandLineArgs = lib.concatStringsSep " " [
#        "--enable-features=UseOzonePlatform,WebUIDarkMode,OverlayScrollbar"
#        "--ozone-platform=wayland"
#        "--force-dark-mode"
#      ];
#    })
#  ];

#  home.packages = with pkgs; [ google-chrome ];

#  programs.google-chrome.enable = true;
#  programs.google-chrome = {
#    enable = true;
#    package = pkgs.google-chrome.override ({
#      commandLineArgs = lib.concatStringsSep " " [
#        "--enable-features=UseOzonePlatform,WebUIDarkMode,OverlayScrollbar"
#        "--ozone-platform=wayland"
#        "--force-dark-mode"
#      ];
#    });
#  };
}
