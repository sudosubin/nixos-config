{ config, pkgs, lib, ... }:
with lib;

let
  inherit (pkgs) stdenv;
  package = if stdenv.isLinux then pkgs.vscodium else pkgs.vscode;
  configDir = if stdenv.isLinux then "${config.xdg.configHome}/VSCodium" else "Library/Application Support/Code";

in
{
  home.file = {
    "${configDir}/product.json".source = ./files/product.json;
    "${configDir}/User/settings.json".source = ./files/settings.json;
    "${configDir}/User/snippets".source = ./files/snippets;
  };

  programs.vscode = {
    enable = true;
    package = package;
    extensions = with pkgs.vscode-extensions; [
      castwide.solargraph
      davidanson.vscode-markdownlint
      dbaeumer.vscode-eslint
      dorzey.vscode-sqlfluff
      eamodio.gitlens
      esbenp.prettier-vscode
      exiasr.hadolint
      flowtype.flow-for-vscode
      fwcd.kotlin
      jnoortheen.nix-ide
      jpoissonnier.vscode-styled-components
      kevinrose.vsc-python-indent
      ms-pyright.pyright
      ms-python.python
      nimsaem.nimvscode
      paulvarache.vscode-taskfile
      pkief.material-icon-theme
      pkief.material-product-icons
      redhat.java
      redhat.vscode-yaml
      rust-lang.rust
      shardulm94.trailing-spaces
      tamasfe.even-better-toml
      timonwong.shellcheck
      usernamehw.errorlens
      yzhang.markdown-all-in-one
      zhuangtongfa.material-theme
    ];
  };

  home.shellAliases = mkIf stdenv.isLinux {
    code = "codium";
  };
}
