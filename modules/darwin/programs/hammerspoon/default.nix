{ config, lib, pkgs, ... }:

{
  services.hammerspoon = {
    enable = true;

    config = {
      HSUploadCrashData = 0;
      MJConfigFile = "~/.config/hammerspoon/init.lua";
    };
  };
}
