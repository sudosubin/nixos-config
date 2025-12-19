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
    # Workaround for nix-vscode-extensions build failures
    # See: https://github.com/nix-community/nix-vscode-extensions/pull/161
    (final: prev: {
      fetchurl =
        args:
        let
          url = args.url or "";
          name = args.name or "";
          isVSCodeExtension =
            lib.any (pattern: builtins.match pattern url != null) [
              ".*gallery\\.vsassets\\.io/.*/extension/.*"
              ".*open-vsx\\.org/.*/file/.*"
            ]
            && lib.hasSuffix ".zip" name;
          patchedArgs =
            if isVSCodeExtension then
              args // { name = builtins.replaceStrings [ ".zip" ] [ ".vsix" ] name; }
            else
              args;
        in
        prev.fetchurl patchedArgs;
    })
    inputs.firefox-addons.overlays.default
    inputs.nix-vscode-extensions.overlays.default
    (final: prev: {
      apple-cursor-theme = final.callPackage ./programs/apple-cursor-theme { };
      cleanshot = final.callPackage ./programs/cleanshot { };
      clop = final.callPackage ./programs/clop { };
      deskpad = final.callPackage ./programs/deskpad { };
      firefox-gnome-theme = final.callPackage ./programs/firefox-gnome-theme { };
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
