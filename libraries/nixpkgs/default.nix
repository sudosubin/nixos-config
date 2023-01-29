{ lib, ... }:

{
  nixpkgs.overlays = [
    (import ./generators)

    (import ./programs/apple-cursor-theme)
    (import ./programs/aws-vault)
    (import ./programs/cleanshot)
    (import ./programs/figma-font-helper)
    (import ./programs/gdb)
    (import ./programs/google-chrome)
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
    "ngrok"
    "raycast"
    "redisinsight"
    "slack"
    "zoom"
  ]);
}
