{
  config,
  pkgs,
  lib,
  ...
}:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin isLinux;

  configDir =
    if isLinux then "${config.xdg.configHome}/Cursor" else "Library/Application Support/Cursor";
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
    code-cursor = pkgs.code-cursor.overrideDerivation (attrs: {
      nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ [ pkgs.nodejs ];

      resources = if isDarwin then "Cursor.app/Contents/Resources" else "resources";

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

    pkief.material-icon-theme =
      pkgs.vscode-marketplace.pkief.material-icon-theme.overrideAttrs
        (attrs: {
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
    "${configDir}/User/snippets".source = ./files/snippets;
  };

  programs.vscode = {
    enable = true;
    package = overlays.code-cursor;
    profiles.default.extensions = with pkgs.vscode-marketplace; [
      adguard.adblock
      arcanis.vscode-zipfs
      bierner.markdown-preview-github-styles
      biomejs.biome
      bradlc.vscode-tailwindcss
      bufbuild.vscode-buf
      casualjim.gotemplate
      charliermarsh.ruff
      davidanson.vscode-markdownlint
      dbaeumer.vscode-eslint
      denoland.vscode-deno
      dorzey.vscode-sqlfluff
      eamodio.gitlens
      editorconfig.editorconfig
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
      ms-kubernetes-tools.vscode-kubernetes-tools
      ms-pyright.pyright
      ms-python.debugpy
      ms-python.python
      overlays.pkief.material-icon-theme # TODO
      pkief.material-product-icons
      prisma.prisma
      redhat.java
      redhat.vscode-yaml
      rust-lang.rust-analyzer
      samuelcolvin.jinjahtml
      shardulm94.trailing-spaces
      styled-components.vscode-styled-components
      svelte.svelte-vscode
      tamasfe.even-better-toml
      teticio.python-envy
      timonwong.shellcheck
      usernamehw.errorlens
      vercel.turbo-vsc
      yoavbls.pretty-ts-errors
      yzhang.markdown-all-in-one
    ];
  };

  home.shellAliases = {
    code = "/usr/bin/open -a Cursor.app";
    cursor = "/usr/bin/open -a Cursor.app";
  };
}
