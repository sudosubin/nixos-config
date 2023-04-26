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
      version = "2023.13.10931546";
      sha256 = "sha256-2FAq5jEbnQbfXa7O9O231aun/pJ8mkoBf1u4ekkBQu8=";
    };

    dorzey.vscode-sqlfluff = vscode-utils.extensionFromVscodeMarketplace {
      name = "vscode-sqlfluff";
      publisher = "dorzey";
      version = "2.2.8";
      sha256 = "1b59gb30hjxhifpkhxajdaxbqil4ajz19m9vmm7zfwbhkcya97nb";
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

    jasonnutter.vscode-codeowners = vscode-utils.extensionFromVscodeMarketplace {
      name = "vscode-codeowners";
      publisher = "jasonnutter";
      version = "1.1.1";
      sha256 = "1bhp1dr9i7vivb0ap43v8rh5r9x8khpjq304kv8p6isjfgqn03vf";
    };

    kevinrose.vsc-python-indent = vscode-utils.extensionFromVscodeMarketplace {
      name = "vsc-python-indent";
      publisher = "kevinrose";
      version = "1.18.0";
      sha256 = "1z8ydwz43znccrhpms0v34236nx4nic65mpfd9ka3w4ng1q8q8w6";
    };

    rust-lang.rust = vscode-utils.extensionFromVscodeMarketplace {
      name = "rust";
      publisher = "rust-lang";
      version = "0.7.9";
      sha256 = "0asmr7c9jmik1047n359s9zmv2m7d0i8sixki4p02z7qzyrpxrfs";
    };
  };
}
