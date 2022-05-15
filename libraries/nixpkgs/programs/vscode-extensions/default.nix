final: { lib, vscode-utils, ... }@prev:

{
  vscode-extensions = lib.recursiveUpdate prev.vscode-extensions {
    arcanis.vscode-zipfs = vscode-utils.extensionFromVscodeMarketplace {
      name = "vscode-zipfs";
      publisher = "arcanis";
      version = "3.0.0";
      sha256 = "sha256-yNRC03kV0UvpEp1gF+NK0N3iCoqZMQ+PAqtrHLXFeXM=";
    };

    bierner.markdown-preview-github-styles = vscode-utils.extensionFromVscodeMarketplace {
      name = "markdown-preview-github-styles";
      publisher = "bierner";
      version = "1.0.1";
      sha256 = "sha256-UhWbygrGh0whVxfGcEa+hunrTG/gfHpXYii0E7YhXa4=";
    };

    dorzey.vscode-sqlfluff = vscode-utils.extensionFromVscodeMarketplace {
      name = "vscode-sqlfluff";
      publisher = "dorzey";
      version = "0.0.5";
      sha256 = "sha256-GuYIapupx8GPekz28j26D8qtICpnfzGoDipuLh/5/pM=";
    };

    exiasr.hadolint = vscode-utils.extensionFromVscodeMarketplace {
      name = "hadolint";
      publisher = "exiasr";
      version = "1.1.1";
      sha256 = "sha256-L8Kg/laHTCADecRJatlUadaT7TnmwD+Bt1pBNS0BRlM=";
    };

    flowtype.flow-for-vscode = vscode-utils.extensionFromVscodeMarketplace {
      name = "flow-for-vscode";
      publisher = "flowtype";
      version = "2.1.0";
      sha256 = "sha256-U0XHNPKV3953zJORaWDwA59aMLX4ZpCIn8VqzqLMHBQ=";
    };

    fwcd.kotlin = vscode-utils.extensionFromVscodeMarketplace {
      name = "kotlin";
      publisher = "fwcd";
      version = "0.2.24";
      sha256 = "sha256-l3SDNS/UO91chDYZ7y8/xboSJ70cBw1Arman5fdNsDg=";
    };

    hashicorp.hcl = vscode-utils.extensionFromVscodeMarketplace {
      name = "hcl";
      publisher = "hashicorp";
      version = "0.1.0";
      sha256 = "sha256-kDf8H0jkRpwSGxpax7USrZd+aQE8O7YGjOJtcL6q1Aw=";
    };

    kevinrose.vsc-python-indent = vscode-utils.extensionFromVscodeMarketplace {
      name = "vsc-python-indent";
      publisher = "kevinrose";
      version = "1.15.0";
      sha256 = "sha256-ZhrwzNJI1yU2ftqJJwWOdrtsnghbLfIJLN53jRZhwIg=";
    };

    nimsaem.nimvscode = vscode-utils.extensionFromVscodeMarketplace {
      name = "nimvscode";
      publisher = "nimsaem";
      version = "0.1.25";
      sha256 = "sha256-f0zDCFmCu7nh0d8jg0lBIJRoDphZX5XUrtqZXd8E2P8=";
    };

    rust-lang.rust = vscode-utils.extensionFromVscodeMarketplace {
      name = "rust";
      publisher = "rust-lang";
      version = "0.7.8";
      sha256 = "sha256-Y33agSNMVmaVCQdYd5mzwjiK5JTZTtzTkmSGTQrSNg0=";
    };

    zhuangtongfa.material-theme = prev.vscode-extensions.zhuangtongfa.material-theme.overrideAttrs (attrs: rec {
      postInstall = ''
        ${attrs.postInstall or ""}

        rm -rf "$out/$installPrefix/styles"
      '';
    });
  };
}
