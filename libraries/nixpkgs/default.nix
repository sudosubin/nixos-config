{
  inputs,
  lib,
  ...
}:

{
  nixpkgs.overlays = [
    inputs.firefox-addons.overlays.default
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
      agent-browser = prev.agent-browser.overrideAttrs (oldAttrs: {
        checkFlags = (oldAttrs.checkFlags or [ ]) ++ [
          "--skip native::parity_tests::test_all_documented_actions_are_handled"
          "--skip native::parity_tests::test_har_start_stop_without_browser"
          "--skip doctor::helpers::tests::test_new_id_is_unique_per_call"
        ];
      });
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
    # Fix: https://github.com/NixOS/nixpkgs/issues/507531
    (
      final: prev:
      lib.optionalAttrs prev.stdenvNoCC.hostPlatform.isDarwin {
        direnv = prev.direnv.overrideAttrs (_: {
          doCheck = false;
        });
      }
    )
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
    (
      final: prev:
      lib.optionalAttrs prev.stdenvNoCC.hostPlatform.isDarwin {
        kiro = prev.kiro.overrideAttrs (oldAttrs: {
          nativeBuildInputs = (oldAttrs.nativeBuildInputs or [ ]) ++ [ prev._7zz ];
          sourceRoot = "Kiro.app";
          postInstall = (oldAttrs.postInstall or "") + ''
            mv "$out/Applications/Kiro.app/Contents/Resources/app/bin/code" \
               "$out/Applications/Kiro.app/Contents/Resources/app/bin/kiro"
          '';
        });
      }
    )
    (final: prev: {
      pi-coding-agent = prev.pi-coding-agent.overrideAttrs (oldAttrs: {
        postInstall =
          builtins.replaceStrings
            [ ''find "$nm/koffi/build/koffi"'' ]
            [ ''! [ -d "$nm/koffi/build/koffi" ] || find "$nm/koffi/build/koffi"'' ]
            oldAttrs.postInstall;
      });
    })
    (final: prev: {
      sqlit-tui = prev.sqlit-tui.overridePythonAttrs (attrs: {
        patches = (attrs.patches or [ ]) ++ [ ./patches/sqlit-tui-sort-connections.patch ];
        dependencies = (attrs.dependencies or [ ]) ++ [ final.python3Packages.pymysql ];
        disabledTestPaths = (attrs.disabledTestPaths or [ ]) ++ [ "tests/ui" ];
        disabledTests = builtins.filter (test: test != "tests/ui/") (attrs.disabledTests or [ ]);
      });
    })
    (final: prev: {
      agent-slack = final.callPackage ./programs/agent-slack { };
      amazon-ember = final.callPackage ./programs/fonts/amazon-ember { };
      apple-cursor-theme = final.callPackage ./programs/apple-cursor-theme { };
      ccusage = final.callPackage ./programs/ccusage { };
      cleanshot = final.callPackage ./programs/cleanshot { };
      clop = final.callPackage ./programs/clop { };
      damn-my-slow-kt = final.callPackage ./programs/damn-my-slow-kt { };
      deepwiki-cli = final.callPackage ./programs/deepwiki-cli { };
      deskpad = final.callPackage ./programs/deskpad { };
      figma-agent = final.callPackage ./programs/figma-agent { };
      gh-attach = final.callPackage ./programs/gh-attach { };

      git-spr = final.callPackage ./programs/git-spr { };
      grep-app-cli = final.callPackage ./programs/grep-app-cli { };
      hammerspoon = final.callPackage ./programs/hammerspoon { };
      homerow = final.callPackage ./programs/homerow { };
      kotlin-lsp = final.callPackage ./programs/kotlin-lsp { };
      kotlin-lsp-wrapper = final.callPackage ./programs/kotlin-lsp-wrapper { };
      kt-speed-client = final.callPackage ./programs/kt-speed-client { };
      linear-cli = final.callPackage ./programs/linear-cli { };
      music-decoy = final.callPackage ./programs/music-decoy { };
      nanum-square = final.callPackage ./programs/fonts/nanum-square { };
      nanum-square-round = final.callPackage ./programs/fonts/nanum-square-round { };
      nix-activate = final.callPackage ./programs/nix-activate { };
      ntn = final.callPackage ./programs/ntn { };
      orca = final.callPackage ./programs/orca { };
      pi-extensions = final.callPackage ./programs/pi-extensions { };
      pravka = final.callPackage ./programs/pravka { };
      pyproject-fmt = final.callPackage ./programs/pyproject-fmt { };
      redisinsight = final.callPackage ./programs/redisinsight { };
      sentry = final.callPackage ./programs/sentry { };
      s-core-dream = final.callPackage ./programs/fonts/s-core-dream { };
      sqlitx = final.callPackage ./programs/sqlitx { };
      wifi-unredactor = final.callPackage ./programs/wifi-unredactor { };
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
      "cleanshot"
      "cursor"
      "cursor-cli"
      "firefox-bin"
      "firefox-bin-unwrapped"
      "homerow"
      "ijhttp"
      "kiro"
      "kiro-cli"
      "kt-speed-client"
      "ngrok"
      "orbstack"
      "postman"
      "redisinsight"
      "sentry"
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
