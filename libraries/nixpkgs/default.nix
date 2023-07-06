{ lib, ... }:

{
  nixpkgs.overlays = [
    (import ./generators)

    (import ./programs/apple-cursor-theme)
    (import ./programs/bob)
    (import ./programs/cleanshot)
    (import ./programs/clop)
    (import ./programs/figma-font-helper)
    (import ./programs/google-chrome)
    (import ./programs/hammerspoon)
    (import ./programs/homerow)
    (import ./programs/orbstack)
    (import ./programs/pragmatapro)
    (import ./programs/python)
    (import ./programs/redisinsight)
    (import ./programs/servicex)
    (import ./programs/vscode-extensions)
    (import ./programs/yabai)
    (import ./programs/zpl-open)
  ];

  nixpkgs.config.allowUnfreePredicate = (pkg: builtins.elem (lib.getName pkg) [
    "1password"
    "1password-cli"
    "cleanshot"
    "datagrip"
    "discord"
    "google-chrome"
    "homerow"
    "ngrok"
    "orbstack"
    "redisinsight"
    "slack"
    "zoom"
  ]);
}
