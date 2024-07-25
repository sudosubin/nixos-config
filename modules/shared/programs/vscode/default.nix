{ config, pkgs, lib, ... }:
with lib;

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin isLinux;

  configDir = if isLinux then "${config.xdg.configHome}/VSCodium" else "Library/Application Support/VSCodium";
  monospace = "'PragmataProMono Nerd Font Mono'";

  stylesheet = {
    ".mac, .windows, .linux" = "--monaco-monospace-font: ${monospace}, monospace !important;";
    ".quick-input-widget" = "font-family: ${monospace} !important;";
    ".search-view .search-widgets-container" = "font-family: ${monospace} !important;";
    ".monaco-tree-sticky-container, .monaco-list-rows, .monaco-findInput, .monaco-inputbox" = "font-family: ${monospace} !important;";
  };

  toCss = stylesheet: strings.concatStrings (attrsets.mapAttrsToList (key: value: "${key}{${value}}") stylesheet);

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
            console.log(crypto.createHash('md5').update(contents).digest('base64').replace(/=+$/, '''));
          """)

          sed -r "s/\"($filename_escaped)\": \"(.*)\"/\"\1\": \"''${checksum//\//\\\/}\"/" \
            -i "$resources/app/product.json"
        }

        echo "${toCss stylesheet}" >> $resources/app/out/vs/workbench/workbench.desktop.main.css
        recalculateChecksum "vs/workbench/workbench.desktop.main.css"
      '';
    });

    pkief.material-icon-theme = pkgs.vscode-marketplace.pkief.material-icon-theme.overrideAttrs (attrs: {
      nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ [ pkgs.nodejs ];

      preInstall = ''
        ${attrs.preInstall or ""}

        node ${./scripts/patch-material-icon-theme.js} "${./files/settings.json}"
      '';
    });

    zhuangtongfa.material-theme = pkgs.vscode-extensions.zhuangtongfa.material-theme.overrideAttrs (attrs: {
      preInstall = ''
        ${attrs.preInstall or ""}
        rm -rf ./styles
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

  programs.vscode = rec {
    enable = true;
    package = overlays.vscodium;
    extensions = with (pkgs.forVSCodeVersion package.version).vscode-marketplace; [
      adguard.adblock
      arcanis.vscode-zipfs
      bierner.markdown-preview-github-styles
      biomejs.biome
      bufbuild.vscode-buf
      casualjim.gotemplate
      pkgs.vscode-extensions.charliermarsh.ruff # TODO
      davidanson.vscode-markdownlint
      pkgs.vscode-extensions.dbaeumer.vscode-eslint # TODO
      denoland.vscode-deno
      dorzey.vscode-sqlfluff
      eamodio.gitlens
      editorconfig.editorconfig
      esbenp.prettier-vscode
      exiasr.hadolint
      foxundermoon.shell-format
      fwcd.kotlin
      golang.go
      graphql.vscode-graphql
      graphql.vscode-graphql-syntax
      hashicorp.terraform
      jnoortheen.nix-ide
      kevinrose.vsc-python-indent
      ms-kubernetes-tools.vscode-kubernetes-tools
      pkgs.vscode-extensions.ms-pyright.pyright # TODO
      ms-python.debugpy
      pkgs.vscode-extensions.ms-python.python # TODO
      overlays.pkief.material-icon-theme # TODO
      pkief.material-product-icons
      prisma.prisma
      redhat.java
      redhat.vscode-yaml
      rust-lang.rust-analyzer
      shardulm94.trailing-spaces
      styled-components.vscode-styled-components
      svelte.svelte-vscode
      tamasfe.even-better-toml
      teticio.python-envy
      timonwong.shellcheck
      usernamehw.errorlens
      yoavbls.pretty-ts-errors
      yzhang.markdown-all-in-one
      overlays.zhuangtongfa.material-theme # TODO
    ];
  };

  home.shellAliases = {
    code = "codium";
  };
}
