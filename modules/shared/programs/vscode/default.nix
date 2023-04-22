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
    ".monaco-list-rows, .monaco-findInput, .monaco-inputbox" = "font-family: ${monospace} !important;";
  };

  toCss = stylesheet: strings.concatStrings (attrsets.mapAttrsToList (key: value: "${key}{${value}}") stylesheet);

  overlays = {
    vscodium = pkgs.vscodium.overrideDerivation (attrs: rec {
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

    pkief.material-icon-theme = pkgs.vscode-extensions.pkief.material-icon-theme.overrideAttrs (attrs: rec {
      nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ [ pkgs.nodejs ];

      preInstall = ''
        ${attrs.preInstall or ""}

        node ${./scripts/patch-material-icon-theme.js} "${./files/settings.json}"
      '';
    });

    zhuangtongfa.material-theme = pkgs.vscode-extensions.zhuangtongfa.material-theme.overrideAttrs (attrs: rec {
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

  programs.vscode = {
    enable = true;
    package = overlays.vscodium;
    extensions = with pkgs.vscode-extensions; [
      arcanis.vscode-zipfs
      bierner.markdown-preview-github-styles
      castwide.solargraph
      casualjim.gotemplate
      charliermarsh.ruff
      davidanson.vscode-markdownlint
      dbaeumer.vscode-eslint
      dorzey.vscode-sqlfluff
      eamodio.gitlens
      editorconfig.editorconfig
      esbenp.prettier-vscode
      exiasr.hadolint
      foxundermoon.shell-format
      fwcd.kotlin
      golang.go
      hashicorp.hcl
      hashicorp.terraform
      jasonnutter.vscode-codeowners
      jnoortheen.nix-ide
      jpoissonnier.vscode-styled-components
      kevinrose.vsc-python-indent
      ms-kubernetes-tools.vscode-kubernetes-tools
      ms-pyright.pyright
      ms-python.python
      nimsaem.nimvscode
      pkief.material-product-icons
      redhat.java
      redhat.vscode-yaml
      rust-lang.rust-analyzer
      shardulm94.trailing-spaces
      shopify.ruby-lsp
      tamasfe.even-better-toml
      timonwong.shellcheck
      usernamehw.errorlens
      yzhang.markdown-all-in-one

      overlays.pkief.material-icon-theme
      overlays.zhuangtongfa.material-theme
    ];
  };

  home.shellAliases = {
    code = "codium";
  };
}
