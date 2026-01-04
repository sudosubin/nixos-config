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
      python3Packages = prev.python3Packages.overrideScope (
        f: p: {
          mcp = p.mcp.overridePythonAttrs (old: {
            postPatch = lib.optionalString pkgs.stdenvNoCC.buildPlatform.isDarwin ''
              substituteInPlace \
                "tests/client/test_stdio.py" \
                "tests/issues/test_552_windows_hang.py" \
                --replace-fail "time.sleep(0.1)" "time.sleep(1)"
              substituteInPlace \
                "tests/shared/test_sse.py" \
                "tests/shared/test_ws.py" \
                --replace-fail "time.sleep(0.5)" "time.sleep(1)"
            '';
          });
          claude-agent-sdk = f.callPackage ./programs/python/claude-agent-sdk { };
        }
      );
      vimPlugins = prev.vimPlugins.extend (
        f: p: {
          spring-boot-nvim = final.callPackage ./programs/vim/spring-boot-nvim { };
        }
      );
    })
    (final: prev: {
      apple-cursor-theme = final.callPackage ./programs/apple-cursor-theme { };
      ccproxy = final.callPackage ./programs/ccproxy { };
      cleanshot = final.callPackage ./programs/cleanshot { };
      clop = final.callPackage ./programs/clop { };
      deskpad = final.callPackage ./programs/deskpad { };
      gemini-mcp-tool = final.callPackage ./programs/gemini-mcp-tool { };
      git-spr = final.callPackage ./programs/git-spr { };
      hammerspoon = final.callPackage ./programs/hammerspoon { };
      homerow = final.callPackage ./programs/homerow { };
      kotlin-lsp = final.callPackage ./programs/kotlin-lsp { };
      nix-activate = final.callPackage ./programs/nix-activate { };
      pragmatapro = final.callPackage ./programs/pragmatapro { };
      redisinsight = final.callPackage ./programs/redisinsight { };
      ruby-lsp-rails = final.callPackage ./programs/ruby-lsp-rails { };
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
      "firefox-bin"
      "firefox-bin-unwrapped"
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
