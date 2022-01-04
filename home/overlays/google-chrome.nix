final: { lib, ... }@prev:

{
  google-chrome = prev.google-chrome.override {
    commandLineArgs = lib.concatStringsSep " " [
      "--enable-features=UseOzonePlatform,WebUIDarkMode,OverlayScrollbar"
      "--ozone-platform=wayland"
      "--force-dark-mode"
    ];
  };
}
