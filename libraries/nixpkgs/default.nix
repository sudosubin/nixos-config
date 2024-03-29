{ inputs, lib, ... }:

{
  nixpkgs.overlays = [
    inputs.nix-vscode-extensions.overlays.default
    (import ./programs/google-chrome)
    (import ./programs/python)

    (final: prev: {
      apple-cursor-theme = final.callPackage ./programs/apple-cursor-theme { };
      cleanshot = final.callPackage ./programs/cleanshot { };
      clop = final.callPackage ./programs/clop { };
      hammerspoon = final.callPackage ./programs/hammerspoon { };
      homerow = final.callPackage ./programs/homerow { };
      ijhttp = final.callPackage ./programs/ijhttp { };
      orbstack = final.callPackage ./programs/orbstack { };
      pragmatapro = final.callPackage ./programs/pragmatapro { };
      redisinsight = final.callPackage ./programs/redisinsight { };
      zpl-open = final.callPackage ./programs/zpl-open { };
    })
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
