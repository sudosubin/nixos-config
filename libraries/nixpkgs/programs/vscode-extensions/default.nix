final: { lib, vscode-utils, ... }@prev:

{
  vscode-extensions = lib.recursiveUpdate prev.vscode-extensions {
    arcanis.vscode-zipfs = vscode-utils.extensionFromVscodeMarketplace {
      name = "vscode-zipfs";
      publisher = "arcanis";
      version = "3.0.0";
      sha256 = "0wvrqnsiqsxb0a7hyccri85f5pfh9biifq4x2bllpl8mg79l5m68";
    };

    bierner.markdown-preview-github-styles = vscode-utils.extensionFromVscodeMarketplace {
      name = "markdown-preview-github-styles";
      publisher = "bierner";
      version = "2.0.2";
      sha256 = "01hxkgw6sjbmj4nhz1a948bz4dzlpjbq9nmw0vnfg64203v9490s";
    };

    casualjim.gotemplate = vscode-utils.extensionFromVscodeMarketplace {
      name = "gotemplate";
      publisher = "casualjim";
      version = "0.4.0";
      sha256 = "0r6219f4gkpic3jjgj1666bwlfpvggf8wrgxp81v38bn9lmydn9g";
    };

    charliermarsh.ruff = vscode-utils.extensionFromVscodeMarketplace {
      name = "ruff";
      publisher = "charliermarsh";
      version = "2023.32.0";
      sha256 = "sha256-phyPQqDgsYunF5FLqPevw8ZZG4Tw9qxjTOU4/kNGKU8=";
    };

    dorzey.vscode-sqlfluff = vscode-utils.extensionFromVscodeMarketplace {
      name = "vscode-sqlfluff";
      publisher = "dorzey";
      version = "2.3.8";
      sha256 = "1q18qqs6x8pv1539ca59vq6aaq51s22yhzaxchxsvh16vs2ypgyz";
    };

    exiasr.hadolint = vscode-utils.extensionFromVscodeMarketplace {
      name = "hadolint";
      publisher = "exiasr";
      version = "1.1.2";
      sha256 = "00x6bnjm0yk0fcw91c47g8c5shgbcvxyyz49r4y23q4gqizvaqz8";
    };

    fwcd.kotlin = vscode-utils.extensionFromVscodeMarketplace {
      name = "kotlin";
      publisher = "fwcd";
      version = "0.2.31";
      sha256 = "1yngrbqndb7jccmakpjv98y8amffvk2zbj3dhz0khdxz6ym18vb3";
    };

    kevinrose.vsc-python-indent = vscode-utils.extensionFromVscodeMarketplace {
      name = "vsc-python-indent";
      publisher = "kevinrose";
      version = "1.18.0";
      sha256 = "1z8ydwz43znccrhpms0v34236nx4nic65mpfd9ka3w4ng1q8q8w6";
    };

    rome.rome = vscode-utils.extensionFromVscodeMarketplace {
      name = "rome";
      publisher = "rome";
      version = "0.25.20230719";
      sha256 = "sha256-umDKW9JH+P3vJQ8pYO2o9fkEFOtvRzWi7XqlJwkVg2E=";
    };

    rust-lang.rust = vscode-utils.extensionFromVscodeMarketplace {
      name = "rust";
      publisher = "rust-lang";
      version = "0.7.9";
      sha256 = "0asmr7c9jmik1047n359s9zmv2m7d0i8sixki4p02z7qzyrpxrfs";
    };

    _42crunch.vscode-openapi = vscode-utils.extensionFromVscodeMarketplace {
      name = "vscode-openapi";
      publisher = "42Crunch";
      version = "4.18.5";
      sha256 = "1r7vkr8jhdf8pxlpx4a6d6mrsm8v9k3rih2yb1sr564w8524bfim";
    };
  };
}
