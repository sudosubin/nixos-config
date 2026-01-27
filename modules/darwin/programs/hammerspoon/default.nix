{
  config,
  pkgs,
  ...
}:

{
  services.hammerspoon = {
    enable = true;

    config = {
      HSUploadCrashData = 0;
      MJConfigFile = "${config.xdg.configHome}/hammerspoon/init.lua";
    };
  };

  xdg.configFile = {
    "hammerspoon/init.lua".source = ./files/init.lua;
    "hammerspoon/Spoons/LeftRightHotkey.spoon".source = pkgs.fetchzip {
      url = "https://github.com/Hammerspoon/Spoons/raw/f11d042ba2212cfe69f4f680b1b219800bb8755e/Spoons/LeftRightHotkey.spoon.zip";
      hash = "sha256-hGCFBEPosqOx6eT6gilFz2DPa/AYjq/TzqeHjiyI6NE=";
    };
  };
}
