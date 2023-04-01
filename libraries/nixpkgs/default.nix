{ lib, ... }:

{
  nixpkgs.overlays = [
    (import ./generators)

    (import ./programs/apple-cursor-theme)
    (import ./programs/cleanshot)
    (import ./programs/clop)
    (import ./programs/figma-font-helper)
    (import ./programs/google-chrome)
    (import ./programs/homerow)
    (import ./programs/pragmatapro)
    (import ./programs/python)
    (import ./programs/raycast)
    (import ./programs/redisinsight)
    (import ./programs/servicex)
    (import ./programs/vscode-extensions)
    (import ./programs/zpl-open)
    (import ./programs/zsh-atuin)
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
    "raycast"
    "redisinsight"
    "slack"
    "zoom"
  ]);
}
