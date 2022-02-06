{ config, pkgs, ... }:

{
  home.packages = with pkgs; [
    vscodium
  ];

  xdg.configFile = {
    "VSCodium/product.json".source = ./files/product.json;
    "VSCodium/User/settings.json".source = ./files/settings.json;
    "VSCodium/User/snippets/typescript.json".source = ./files/snippets/typescript.json;
    "VSCodium/User/snippets/typescriptreact.json".source = ./files/snippets/typescriptreact.json;
  };

  programs.vscode = {
    enable = true;
    package = pkgs.vscodium;
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
}
