{ config, lib, pkgs, ... }:

{
  home.packages = with pkgs; [
    himalaya
  ];

  programs.himalaya = {
    enable = true;

    settings = {
      name = "Subin Kim";
      downloads-dir = "~/Downloads";
      default-page-size = 50;
    };
  };
}
