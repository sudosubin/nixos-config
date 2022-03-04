{ config, pkgs, lib, ... }:

{
  services.figma-font-helper = {
    enable = true;

    directories = [ "${config.home.path}/share/fonts" ];
  };
}
