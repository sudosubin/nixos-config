final: { lib, vscode-utils, ... }@prev:

{
  vscode-extensions = lib.recursiveUpdate prev.vscode-extensions {
    exiasr.hadolint = vscode-utils.extensionFromVscodeMarketplace {
      name = "hadolint";
      publisher = "exiasr";
      version = "1.1.0";
      sha256 = "sha256-pMzWqlfuNC5IakAoOr3rekQexz8eIouM6i4HvFwh7oY=";
    };

    flowtype.flow-for-vscode = vscode-utils.extensionFromVscodeMarketplace {
      name = "flow-for-vscode";
      publisher = "flowtype";
      version = "1.9.2";
      sha256 = "sha256-DFjWdnH4m8sw/bR2ti89CKX0WrWe3bPRN8C9ysSjsa0=";
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

    ms-pyright.pyright = vscode-utils.extensionFromVscodeMarketplace {
      name = "pyright";
      publisher = "ms-pyright";
      version = "1.1.215";
      sha256 = "sha256-GIRs6wWKYkgMcTKAkykcRmNjWv1A/bqQk3eF1ucKw+k=";
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
  };
}
