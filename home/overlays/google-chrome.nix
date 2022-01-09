final: { lib, ... }@prev:

{
  google-chrome = prev.google-chrome.override {
    commandLineArgs = lib.concatStringsSep " " [
      "--enable-features=WebUIDarkMode,OverlayScrollbar"
      "--force-dark-mode"
    ];
  };
}
