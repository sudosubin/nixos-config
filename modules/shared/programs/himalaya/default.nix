{ config, lib, pkgs, ... }:

{
  programs.himalaya = {
    enable = true;

    settings = {
      name = "Subin Kim";
      downloads-dir = "~/Downloads";
      default-page-size = 50;
    };
  };
}
