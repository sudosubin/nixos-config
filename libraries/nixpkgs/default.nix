{ inputs, lib, ... }:

{
  nixpkgs.overlays = [
    inputs.nix-vscode-extensions.overlays.default
    (import ./programs/apple-cursor-theme)
    (import ./programs/cleanshot)
    (import ./programs/clop)
    (import ./programs/figma-font-helper)
    (import ./programs/google-chrome)
    (import ./programs/hadolint)
    (import ./programs/hammerspoon)
    (import ./programs/homerow)
    (import ./programs/ijhttp)
    (import ./programs/orbstack)
    (import ./programs/pragmatapro)
    (import ./programs/python)
    (import ./programs/redisinsight)
    (import ./programs/zpl-open)
  ];

  nixpkgs.config.allowUnfreePredicate = (pkg: builtins.elem (lib.getName pkg) [
    "1password"
    "1password-cli"
    "cleanshot"
    "datagrip"
    "google-chrome"
    "homerow"
    "ijhttp"
    "ngrok"
    "orbstack"
    "redisinsight"
    "slack"
    "zoom"
  ]);

  nixpkgs.config.permittedInsecurePackages = [
    "figma-linux-0.10.0"
  ];
}
