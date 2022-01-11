{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    vscodium
  ];

  xdg.configFile = {
    "VSCodium/product.json".source = ../files/vscode/product.json;
    "VSCodium/User/settings.json".source = ../files/vscode/settings.json;
    "VSCodium/User/snippets/typescript.json".source = ../files/vscode/snippets/typescript.json;
    "VSCodium/User/snippets/typescriptreact.json".source = ../files/vscode/snippets/typescriptreact.json;
  };

  programs.vscode = {
    enable = true;
    package = pkgs.vscodium;
    extensions = with pkgs.vscode-extensions; [
      bbenoist.nix
      davidanson.vscode-markdownlint
      dbaeumer.vscode-eslint
      eamodio.gitlens
      esbenp.prettier-vscode
      jpoissonnier.vscode-styled-components
      ms-python.vscode-pylance
      ms-vsliveshare.vsliveshare
      pkief.material-icon-theme
      redhat.java
      shardulm94.trailing-spaces
      tamasfe.even-better-toml
      timonwong.shellcheck
      usernamehw.errorlens
      yzhang.markdown-all-in-one
      zhuangtongfa.material-theme
      # exiasr.hadolint
      # flowtype.flow-for-vscode
      # fwcd.kotlin
      # iocave.customize-ui
      # iocave.monkey-patch
      # kevinrose.vsc-python-indent
      # nimsaem.nimvscode
      # rust-lang.rust
    ];
  };
}
