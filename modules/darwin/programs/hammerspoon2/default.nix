{
  config,
  lib,
  osConfig,
  ...
}:

let
  inherit (config.home) homeDirectory username;
  inherit (osConfig.environment) systemPath;

in
{
  services.hammerspoon2 = {
    enable = true;

    # launchd doesn't expand $HOME/$USER
    environment.PATH = lib.replaceStrings [ "$HOME" "$USER" ] [ homeDirectory username ] systemPath;

    config = {
      configLocation = "${config.xdg.configHome}/hammerspoon2/init.js";
      dockMenuBehaviour = "menuBar";
      hasCompletedOnboarding = true;
    };
  };

  xdg.configFile = {
    "hammerspoon2/init.js".source = ./files/init.js;
    "hammerspoon2/Spoons/TextReplacement".source = ./spoons/TextReplacement;
  };
}
