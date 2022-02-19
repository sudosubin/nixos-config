{ config, pkgs, lib, ... }:
with lib;

let
  inherit (pkgs) stdenv;
  package = if stdenv.isLinux then pkgs.vscodium else pkgs.vscode;
  configDir = if stdenv.isLinux then "${config.xdg.configHome}/VSCodim" else "Library/Application Support/Code";

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
      bbenoist.nix
      castwide.solargraph
      davidanson.vscode-markdownlint
      dbaeumer.vscode-eslint
      eamodio.gitlens
      esbenp.prettier-vscode
      exiasr.hadolint
      flowtype.flow-for-vscode
      fwcd.kotlin
      jpoissonnier.vscode-styled-components
      kevinrose.vsc-python-indent
      ms-pyright.pyright
      ms-python.python
      nimsaem.nimvscode
      pkief.material-icon-theme
      pkief.material-product-icons
      redhat.java
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
