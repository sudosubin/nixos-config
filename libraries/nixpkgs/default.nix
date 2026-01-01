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
    (final: prev: {
      apple-cursor-theme = final.callPackage ./programs/apple-cursor-theme { };
      ccproxy-api = final.callPackage ./programs/ccproxy-api { };
      claude-code-api = final.callPackage ./programs/claude-code-api { };
      cleanshot = final.callPackage ./programs/cleanshot { };
      clop = final.callPackage ./programs/clop { };
      deskpad = final.callPackage ./programs/deskpad { };
      gemini-mcp-tool = final.callPackage ./programs/gemini-mcp-tool { };
      git-spr = final.callPackage ./programs/git-spr { };
      hammerspoon = final.callPackage ./programs/hammerspoon { };
      homerow = final.callPackage ./programs/homerow { };
      nix-activate = final.callPackage ./programs/nix-activate { };
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
      "amp-cli"
      "claude-code"
      "cleanshot"
      "cursor"
      "cursor-cli"
      "datagrip"
      "homerow"
      "idea"
      "ijhttp"
      "ngrok"
      "postman"
      "pragmatapro"
      "redisinsight"
      "slack"
      "vscode-extension-anthropic-claude-code"
      # pkgs.firefox-addons
      "onepassword-password-manager"
    ]
  );

  nixpkgs.config.permittedInsecurePackages = [
    "figma-linux-0.10.0"
  ];
}
