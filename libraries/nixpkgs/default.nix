{ inputs, lib, pkgs, ... }:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;

in
{
  nixpkgs.overlays = [
    inputs.nix-vscode-extensions.overlays.default
    (import ./programs/google-chrome)
    (import ./programs/python)

    (final: prev: {
      apple-cursor-theme = final.callPackage ./programs/apple-cursor-theme { };
      clop = final.callPackage ./programs/clop { };
      git-spr = final.callPackage ./programs/git-spr { };
      hammerspoon = final.callPackage ./programs/hammerspoon { };
      homerow = final.callPackage ./programs/homerow { };
      ijhttp = final.callPackage ./programs/ijhttp { };
      orbstack = final.callPackage ./programs/orbstack { };
      pragmatapro = final.callPackage ./programs/pragmatapro { };
      redisinsight = final.callPackage ./programs/redisinsight { };
      shottr = final.callPackage ./programs/shottr { };
      zpl-open = final.callPackage ./programs/zpl-open { };
    })
  ];

  nixpkgs.config.allowUnfreePredicate = (pkg: builtins.elem (lib.getName pkg) [
    "1password"
    "1password-cli"
    "datagrip"
    "google-chrome"
    "homerow"
    "ijhttp"
    "ngrok"
    "orbstack"
    "redisinsight"
    "shottr"
    "slack"
    "zoom"
  ]);

  nixpkgs.config.permittedInsecurePackages = [
    "figma-linux-0.10.0"
  ];
}
