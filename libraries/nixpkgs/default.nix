{ lib, ... }:

{
  nixpkgs.overlays = [
    (import ./generators/xml.nix)

    (import ./programs/alfred5)
    (import ./programs/apple-cursor-theme)
    (import ./programs/aws-vault)
    (import ./programs/figma-font-helper)
    (import ./programs/google-chrome)
    (import ./programs/pragmatapro)
    (import ./programs/python)
    (import ./programs/raycast)
    (import ./programs/servicex)
    (import ./programs/slack-cli-bin)
    (import ./programs/vscode-extensions)
    (import ./programs/yabai)
    (import ./programs/zpl-open)
    (import ./programs/zsh-atuin)
  ];

  nixpkgs.config.allowUnfreePredicate = (pkg: builtins.elem (lib.getName pkg) [
    "1password-cli"
    "alfred"
    "datagrip"
    "google-chrome"
    "ngrok"
    "raycast"
    "slack"
    "slack-cli-bin"
    "zoom"
  ]);
}
