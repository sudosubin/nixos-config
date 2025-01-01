{ config, lib, pkgs, ... }:

{
  services.raycast = {
    enable = true;

    config = {
      navigationCommandStyleIdentifierKey = "vim";
      raycastGlobalHotkey = "Command-49";
      raycastPreferredWindowMode = "compact";
    };
  };
}
