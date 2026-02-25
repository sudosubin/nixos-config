{
  config,
  lib,
  pkgs,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin isLinux;

  configDir =
    if isLinux then "${config.xdg.configHome}/VSCodium" else "Library/Application Support/VSCodium";
  monospace = "'PragmataProMono Nerd Font Mono'";

  stylesheet = {
    ".mac, .windows, .linux" = "font-family: ${monospace}, monospace !important;";
    ".quick-input-widget" = "font-family: ${monospace} !important;";
    ".search-view .search-widgets-container" = "font-family: ${monospace} !important;";
    ".monaco-workbench .debug-pane .monaco-list-row .expression" =
      "font-family: ${monospace} !important;";
    ".monaco-tree-sticky-container, .monaco-list-rows, .monaco-findInput, .monaco-inputbox" =
      "font-family: ${monospace} !important;";
  };

  toCss =
    stylesheet:
    lib.strings.concatStrings (lib.attrsets.mapAttrsToList (key: value: "${key}{${value}}") stylesheet);

  overlays = {
    vscodium = pkgs.vscodium.overrideDerivation (attrs: {
      nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ [ pkgs.nodejs ];

      resources = if isDarwin then "Contents/Resources" else "resources";

      preInstall = ''
        ${attrs.preInstall or ""}

        recalculateChecksum() {
          filename="$1"
          filename_escaped="$(echo "$filename" | sed "s/\//\\\\\//g" | sed "s/\./\\\\\./g")"

          checksum=$(node -e """
            const crypto = require('crypto');
            const fs = require('fs');

            const contents = fs.readFileSync('$resources/app/out/$filename');
            console.log(crypto.createHash('sha256').update(contents).digest('base64').replace(/=+$/, '''));
          """)

          sed -r "s/\"($filename_escaped)\": \"(.*)\"/\"\1\": \"''${checksum//\//\\\/}\"/" \
            -i "$resources/app/product.json"
        }

        echo "${toCss stylesheet}" >> $resources/app/out/vs/workbench/workbench.desktop.main.css
        recalculateChecksum "vs/workbench/workbench.desktop.main.css"
      '';
    });

    pkief.material-icon-theme = pkgs.open-vsx.pkief.material-icon-theme.overrideAttrs (attrs: {
      nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ [ pkgs.nodejs ];

      preInstall = ''
        ${attrs.preInstall or ""}

        node ${./scripts/patch-material-icon-theme.js} "${./files/settings.json}"
      '';
    });
  };

in
{
  home.file = {
    "${configDir}/product.json".source = ./files/product.json;
    "${configDir}/User/settings.json".source = ./files/settings.json;
  };

  programs.vscode = rec {
    enable = true;
    package = overlays.vscodium;
    profiles.default.extensions =
      (with (pkgs.forVSCodeVersion package.vscodeVersion).open-vsx; [
        adguard.adblock
        anthropic.claude-code
        arcanis.vscode-zipfs
        astral-sh.ty
        bierner.markdown-preview-github-styles
        biomejs.biome
        bradlc.vscode-tailwindcss
        bufbuild.vscode-buf
        charliermarsh.ruff
        coderabbit.coderabbit-vscode
        davidanson.vscode-markdownlint
        dbaeumer.vscode-eslint
        denoland.vscode-deno
        esbenp.prettier-vscode
        exiasr.hadolint
        foxundermoon.shell-format
        fwcd.kotlin
        github.github-vscode-theme
        golang.go
        graphql.vscode-graphql
        graphql.vscode-graphql-syntax
        hashicorp.terraform
        jnoortheen.nix-ide
        kevinrose.vsc-python-indent
        ms-pyright.pyright
        ms-python.debugpy
        ms-python.python
        pkief.material-product-icons
        prisma.prisma
        redhat.java
        redhat.vscode-yaml
        rust-lang.rust-analyzer
        samuelcolvin.jinjahtml
        shardulm94.trailing-spaces
        styled-components.vscode-styled-components
        tamasfe.even-better-toml
        teticio.python-envy
        timonwong.shellcheck
        usernamehw.errorlens
        vercel.turbo-vsc
        yoavbls.pretty-ts-errors
        yzhang.markdown-all-in-one
      ])
      ++ (with (pkgs.forVSCodeVersion package.vscodeVersion).open-vsx-release; [
        eamodio.gitlens
      ])
      ++ (with (pkgs.forVSCodeVersion package.vscodeVersion).vscode-marketplace; [
        sweepai.sweep-nes
      ])
      ++ [
        overlays.pkief.material-icon-theme
      ];
  };

  home.shellAliases = {
    code = "codium";
  };
}
