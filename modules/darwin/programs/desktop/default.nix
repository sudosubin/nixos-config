{ ... }:

{
  targets.darwin.copyApps.enable = true;
  targets.darwin.linkApps.enable = false;

  targets.darwin.defaults = {
    NSGlobalDomain.AppleLanguages = [
      "en-US"
      "ko-KR"
    ];
    NSGlobalDomain.AppleLocale = "en_US";

    "com.apple.desktopservices" = {
      DSDontWriteNetworkStores = true;
      DSDontWriteUSBStores = true;
    };
  };

  targets.darwin.keybindings = {
    "₩" = [
      "insertText:"
      "`"
    ];
  };
}
