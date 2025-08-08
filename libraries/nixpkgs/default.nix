{
  inputs,
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;

in
{
  nixpkgs.overlays = [
    inputs.firefox-addons.overlays.default
    inputs.nix-vscode-extensions.overlays.default
    (import ./programs/python)

    (final: prev: {
      apple-cursor-theme = final.callPackage ./programs/apple-cursor-theme { };
      cleanshot = final.callPackage ./programs/cleanshot { };
      clop = final.callPackage ./programs/clop { };
      cursor-agent = final.callPackage ./programs/cursor-agent { };
      deskpad = final.callPackage ./programs/deskpad { };
      firefox-gnome-theme = final.callPackage ./programs/firefox-gnome-theme { };
      git-spr = final.callPackage ./programs/git-spr { };
      hammerspoon = final.callPackage ./programs/hammerspoon { };
      homerow = final.callPackage ./programs/homerow { };
      nix-activate = final.callPackage ./programs/nix-activate { };
      o3-search-mcp = final.callPackage ./programs/o3-search-mcp { };
      pragmatapro = final.callPackage ./programs/pragmatapro { };
      redisinsight = final.callPackage ./programs/redisinsight { };
      zpl-open = final.callPackage ./programs/zpl-open { };
    })
  ];

  nixpkgs.config.allowUnfreePredicate = (
    pkg:
    builtins.elem (lib.getName pkg) [
      # pkgs
      "1password"
      "1password-cli"
      "claude-code"
      "cleanshot"
      "cursor"
      "cursor-agent"
      "datagrip"
      "homerow"
      "idea-ultimate"
      "ijhttp"
      "ngrok"
      "postman"
      "pragmatapro"
      "raycast"
      "redisinsight"
      "slack"
      # pkgs.firefox-addons
      "onepassword-password-manager"
    ]
  );

  nixpkgs.config.permittedInsecurePackages = [
    "figma-linux-0.10.0"
  ];
}
