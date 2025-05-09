{
  config,
  pkgs,
  lib,
  ...
}:

{
  programs.chromium-patched = {
    enable = true;
    package = pkgs.ungoogled-chromium;
    commandLineArgs = [
      "--webrtc-ip-handling-policy=default_public_interface_only"
    ];
    extensions = [
      pkgs.chrome-web-store._1password-password-manager
      pkgs.chrome-web-store.google-translate
      pkgs.chrome-web-store.neutral-face-emoji-tools
      pkgs.chrome-web-store.ublock-origin-lite
    ];
  };
}
