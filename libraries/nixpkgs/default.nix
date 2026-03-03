{
  inputs,
  lib,
  pkgs,
  ...
}:

{
  nixpkgs.overlays = [
    inputs.nix-chrome-extensions.overlays.default
    inputs.nix-skills.overlays.default
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
    # Fix: https://github.com/eza-community/eza/issues/1224
    (
      final: prev:
      lib.optionalAttrs prev.stdenvNoCC.hostPlatform.isDarwin {
        eza = prev.eza.overrideAttrs (oldAttrs: {
          nativeBuildInputs = (oldAttrs.nativeBuildInputs or [ ]) ++ [ prev.makeWrapper ];
          postInstall = ''
            ${oldAttrs.postInstall or ""}
            wrapProgram $out/bin/eza \
              --run 'export EZA_CONFIG_DIR="''${EZA_CONFIG_DIR:-''${XDG_CONFIG_HOME:-$HOME/.config}/eza}"'
          '';
        });
      }
    )
    (final: prev: {
      sqlit-tui = prev.sqlit-tui.overridePythonAttrs (attrs: {
        dependencies = (attrs.dependencies or [ ]) ++ [ final.python3Packages.pymysql ];
      });
    })
    (final: prev: {
      tombi = prev.tombi.overrideAttrs (oldAttrs: rec {
        version = "0.8.0";
        src = prev.fetchFromGitHub {
          owner = "tombi-toml";
          repo = "tombi";
          tag = "v${version}";
          hash = "sha256-rVXLfE6J2WI8mD2apKzDuDblQxaccSWggsUgcpom+2U=";
        };
        cargoDeps = prev.rustPlatform.fetchCargoVendor {
          inherit src;
          hash = "sha256-5EZNL5aBdS+1TI4Gx2AQw6Di+5rYQBR3ukexSnFFIcs=";
        };
      });
    })
    (final: prev: {
      agent-browser = final.callPackage ./programs/agent-browser { };
      amazon-ember = final.callPackage ./programs/fonts/amazon-ember { };
      apple-cursor-theme = final.callPackage ./programs/apple-cursor-theme { };
      ccusage = final.callPackage ./programs/ccusage { };
      ccusage-pi = final.callPackage ./programs/ccusage-pi { };
      claude-code-bin = final.callPackage ./programs/claude-code-bin { };
      cleanshot = final.callPackage ./programs/cleanshot { };
      clop = final.callPackage ./programs/clop { };
      deepwiki-cli = final.callPackage ./programs/deepwiki-cli { };
      deskpad = final.callPackage ./programs/deskpad { };
      gh-attach = final.callPackage ./programs/gh-attach { };
      git-spr = final.callPackage ./programs/git-spr { };
      grep-app-cli = final.callPackage ./programs/grep-app-cli { };
      hammerspoon = final.callPackage ./programs/hammerspoon { };
      homerow = final.callPackage ./programs/homerow { };
      kotlin-lsp = final.callPackage ./programs/kotlin-lsp { };
      kotlin-lsp-wrapper = final.callPackage ./programs/kotlin-lsp-wrapper { };
      linear-cli = final.callPackage ./programs/linear-cli { };
      music-decoy = final.callPackage ./programs/music-decoy { };
      nanum-square = final.callPackage ./programs/fonts/nanum-square { };
      nanum-square-round = final.callPackage ./programs/fonts/nanum-square-round { };
      nix-activate = final.callPackage ./programs/nix-activate { };
      pi = final.callPackage ./programs/pi { };
      pi-extensions = final.callPackage ./programs/pi-extensions { };
      pragmatapro = final.callPackage ./programs/pragmatapro { };
      pyproject-fmt = final.callPackage ./programs/pyproject-fmt { };
      redisinsight = final.callPackage ./programs/redisinsight { };
      s-core-dream = final.callPackage ./programs/fonts/s-core-dream { };
      ungoogled-chromium = lib.optionals prev.stdenvNoCC.hostPlatform.isDarwin (
        final.callPackage ./programs/ungoogled-chromium { }
      );
      wtp = final.callPackage ./programs/wtp { };
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
      "google-chrome"
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
    "google-chrome-144.0.7559.97"
  ];
}
