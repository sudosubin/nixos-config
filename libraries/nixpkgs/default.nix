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
      lib.optionalAttrs prev.stdenvNoCC.hostPlatform.isDarwin {
        direnv = prev.direnv.overrideAttrs (_: {
          # nixpkgs disables cgo for direnv, but upstream's Darwin makefile still adds
          # `-linkmode=external`, which requires cgo. Override the final go build flags.
          buildPhase = ''
            make GO_BUILD_FLAGS="-ldflags '-X main.bashPath=$BASH_PATH'" BASH_PATH=$BASH_PATH
          '';
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
    # Fix: https://github.com/NixOS/nixpkgs/pull/509438
    (
      final: prev:
      lib.optionalAttrs prev.stdenvNoCC.hostPlatform.isDarwin {
        duckdb = prev.duckdb.overrideAttrs (oldAttrs: {
          installCheckPhase =
            let
              extraExcludes = lib.concatStringsSep " " (
                map (pattern: "exclude:'${pattern}'") [
                  "test/sql/join/iejoin/iejoin_issue_6314.test_slow"
                  "test/sql/join/iejoin/test_iejoin_sort_tasks.test_slow"
                  "test/sql/join/asof/test_asof_join_inequalities.test"
                  "test/sql/join/asof/test_asof_join_missing.test_slow"
                  "test/sql/join/test_complex_range_join.test"
                ]
              );
            in
            lib.replaceStrings [ "./test/unittest" ] [ "./test/unittest ${extraExcludes}" ]
              oldAttrs.installCheckPhase;
        });
      }
    )
    # Fix: https://github.com/NixOS/nixpkgs/pull/507400
    (
      final: prev:
      let
        buildVscode = prev.callPackage (prev.path + "/pkgs/applications/editors/vscode/generic.nix") {
          glibc = if prev.stdenv.hostPlatform.isLinux then prev.glibc else { bin = null; };
        };
      in
      {
        code-cursor = prev.callPackage (prev.path + "/pkgs/by-name/co/code-cursor/package.nix") {
          inherit buildVscode;
        };
      }
    )
    (final: prev: {
      sqlit-tui = prev.sqlit-tui.overridePythonAttrs (attrs: {
        dependencies = (attrs.dependencies or [ ]) ++ [ final.python3Packages.pymysql ];
        disabledTestPaths = (attrs.disabledTestPaths or [ ]) ++ [ "tests/ui" ];
        disabledTests = builtins.filter (test: test != "tests/ui/") (attrs.disabledTests or [ ]);
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
      gh-stack = final.callPackage ./programs/gh-stack { };
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
      sentry = final.callPackage ./programs/sentry { };
      s-core-dream = final.callPackage ./programs/fonts/s-core-dream { };
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
      "firefox-bin"
      "firefox-bin-unwrapped"
      "homerow"
      "idea"
      "ijhttp"
      "ngrok"
      "orbstack"
      "postman"
      "pragmatapro"
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
