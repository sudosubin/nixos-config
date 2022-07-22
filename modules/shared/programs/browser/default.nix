{ config, pkgs, ... }:

{
  programs.firefox = {
    enable = true;
    package = pkgs.firefox-beta-bin;
    extensions = with pkgs.firefox-addons; [
      _1password-x-password-manager
      darkreader
      react-devtools
      ublock-origin
    ];
    profiles = {
      sudosubin = {
        name = "sudosubin";
        id = 0;
        settings = {
          "extensions.update.enabled" = false;
        };
      };
    };
  };
}
