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
    inputs.nix-chrome-extensions.overlays.default
    inputs.nix-vscode-extensions.overlays.default
    (final: prev: {
      python3Packages = prev.python3Packages.overrideScope (
        f: p: {
          toml-fmt-common = f.callPackage ./programs/python/toml-fmt-common { };
        }
      );
    })
    (final: prev: {
      bash-language-server = prev.bash-language-server.overrideAttrs (attrs: {
        installPhase = ''
          runHook preInstall

          mkdir -p $out/{bin,lib/bash-language-server}
          cp -r {node_modules,server} $out/lib/bash-language-server/

          # Create the executable, based upon what happens in npmHooks.npmInstallHook
          makeWrapper ${lib.getExe prev.nodejs} $out/bin/bash-language-server \
            --suffix PATH : ${
              lib.makeBinPath [
                prev.shellcheck
                prev.shfmt
              ]
            } \
            --inherit-argv0 \
            --add-flags $out/lib/bash-language-server/server/out/cli.js

          runHook postInstall
        '';
      });
    })
    (
      final: prev:
      (lib.mkIf isDarwin {
        ungoogled-chromium = final.callPackage ./programs/ungoogled-chromium { };
      })
    )
    (final: prev: {
      amazon-ember = final.callPackage ./programs/fonts/amazon-ember { };
      apple-cursor-theme = final.callPackage ./programs/apple-cursor-theme { };
      claude-code-bin = final.callPackage ./programs/claude-code-bin { };
      cleanshot = final.callPackage ./programs/cleanshot { };
      clop = final.callPackage ./programs/clop { };
      deskpad = final.callPackage ./programs/deskpad { };
      gemini-mcp-tool = final.callPackage ./programs/gemini-mcp-tool { };
      git-spr = final.callPackage ./programs/git-spr { };
      hammerspoon = final.callPackage ./programs/hammerspoon { };
      homerow = final.callPackage ./programs/homerow { };
      kotlin-lsp = final.callPackage ./programs/kotlin-lsp { };
      kotlin-lsp-wrapper = final.callPackage ./programs/kotlin-lsp-wrapper { };
      linear-cli = final.callPackage ./programs/linear-cli { };
      nanum-square-round = final.callPackage ./programs/fonts/nanum-square-round { };
      nix-activate = final.callPackage ./programs/nix-activate { };
      pi-coding-agent = final.callPackage ./programs/pi-coding-agent { };
      pragmatapro = final.callPackage ./programs/pragmatapro { };
      pyproject-fmt = final.callPackage ./programs/pyproject-fmt { };
      redisinsight = final.callPackage ./programs/redisinsight { };
      s-core-dream = final.callPackage ./programs/fonts/s-core-dream { };
      ungoogled-chromium = final.callPackage ./programs/ungoogled-chromium { };
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
      "claude-code-bin"
      "cleanshot"
      "cursor"
      "cursor-cli"
      "datagrip"
      "homerow"
      "idea"
      "ijhttp"
      "ngrok"
      "orbstack"
      "postman"
      "pragmatapro"
      "redisinsight"
      "slack"
      "vscode-extension-anthropic-claude-code"
      "onepassword-password-manager"
    ]
  );

  nixpkgs.config.permittedInsecurePackages = [
    "figma-linux-0.10.0"
  ];
}
