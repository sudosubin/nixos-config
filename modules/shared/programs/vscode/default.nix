{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    vscodium
  ];

  xdg.configFile = {
    "VSCodium/product.json".source = ./vscode/product.json;
    "VSCodium/User/settings.json".source = ./vscode/settings.json;
    "VSCodium/User/snippets/typescript.json".source = ./vscode/snippets/typescript.json;
    "VSCodium/User/snippets/typescriptreact.json".source = ./vscode/snippets/typescriptreact.json;
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
      exiasr.hadolint
      flowtype.flow-for-vscode
      fwcd.kotlin
      jpoissonnier.vscode-styled-components
      kevinrose.vsc-python-indent
      ms-python.python
      ms-python.vscode-pylance
      ms-vsliveshare.vsliveshare
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
}
