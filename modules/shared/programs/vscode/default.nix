{ config, pkgs, lib, ... }:
with lib;

let
  inherit (pkgs) stdenv;
  configDir = if stdenv.isLinux then "${config.xdg.configHome}/VSCodium" else "Library/Application Support/VSCodium";

  # vscodium = pkgs.vscodium.overrideAttrs

  overlays = {
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
    package = pkgs.vscodium;
    extensions = with pkgs.vscode-extensions; [
      arcanis.vscode-zipfs
      bierner.markdown-preview-github-styles
      casualjim.gotemplate
      davidanson.vscode-markdownlint
      dbaeumer.vscode-eslint
      dorzey.vscode-sqlfluff
      eamodio.gitlens
      editorconfig.editorconfig
      esbenp.prettier-vscode
      exiasr.hadolint
      flowtype.flow-for-vscode
      foxundermoon.shell-format
      fwcd.kotlin
      golang.go
      hashicorp.hcl
      hashicorp.terraform
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
      rust-lang.rust
      shardulm94.trailing-spaces
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
