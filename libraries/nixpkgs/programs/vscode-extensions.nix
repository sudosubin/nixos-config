final: { lib, vscode-utils, ... }@prev:

{
  vscode-extensions = lib.recursiveUpdate prev.vscode-extensions {
    castwide.solargraph = vscode-utils.extensionFromVscodeMarketplace {
      name = "solargraph";
      publisher = "castwide";
      version = "0.23.0";
      sha256 = "sha256-1qQY7WMTxEsf3fQRoV+h1eFFBfGDRU6wkCIcE7Dnakc=";
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
      version = "1.1.0";
      sha256 = "sha256-pMzWqlfuNC5IakAoOr3rekQexz8eIouM6i4HvFwh7oY=";
    };

    flowtype.flow-for-vscode = vscode-utils.extensionFromVscodeMarketplace {
      name = "flow-for-vscode";
      publisher = "flowtype";
      version = "2.0.0";
      sha256 = "sha256-QGs0GwDEsfUdg41R3nYvLTUmERDnzb3j2BO5749dQCs=";
    };

    fwcd.kotlin = vscode-utils.extensionFromVscodeMarketplace {
      name = "kotlin";
      publisher = "fwcd";
      version = "0.2.23";
      sha256 = "sha256-nKhQrDdpKnZmC5nnfSTevUES1G6H8WNlLF26zFWnTmQ=";
    };

    kevinrose.vsc-python-indent = vscode-utils.extensionFromVscodeMarketplace {
      name = "vsc-python-indent";
      publisher = "kevinrose";
      version = "1.14.2";
      sha256 = "sha256-T0uPywFo0it/4GNNaC8c8vGxHxkr/4S1Pz7ObtNrSMM=";
    };

    nimsaem.nimvscode = vscode-utils.extensionFromVscodeMarketplace {
      name = "nimvscode";
      publisher = "nimsaem";
      version = "0.1.25";
      sha256 = "sha256-f0zDCFmCu7nh0d8jg0lBIJRoDphZX5XUrtqZXd8E2P8=";
    };

    paulvarache.vscode-taskfile = vscode-utils.extensionFromVscodeMarketplace {
      name = "vscode-taskfile";
      publisher = "paulvarache";
      version = "0.0.5";
      sha256 = "sha256-SdqTfQoSt+YNUrYOg95VEErWkK4EnJNYKQOE1kc1+k8=";
    };

    rust-lang.rust = vscode-utils.extensionFromVscodeMarketplace {
      name = "rust";
      publisher = "rust-lang";
      version = "0.7.8";
      sha256 = "sha256-Y33agSNMVmaVCQdYd5mzwjiK5JTZTtzTkmSGTQrSNg0=";
    };
  };
}
