{
  config,
  lib,
  pkgs,
  ...
}:

{
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
