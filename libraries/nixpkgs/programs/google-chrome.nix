final: { lib, ... }@prev:

{
  google-chrome = prev.google-chrome.override {
    commandLineArgs = lib.concatStringsSep " " [
      "--enable-features=WebRTCPipeWireCapturer,WebUIDarkMode,OverlayScrollbar"
      "--force-dark-mode"
    ];
  };
}
