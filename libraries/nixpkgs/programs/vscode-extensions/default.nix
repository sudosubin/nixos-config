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
      version = "2.0.3";
      sha256 = "1dlw0p9zkv0dy5bf6byd0l40f5r9200anw20ps75vldgji67mqfa";
    };

    biomejs.biome = vscode-utils.extensionFromVscodeMarketplace {
      name = "biome";
      publisher = "biomejs";
      version = "1.5.20231014";
      sha256 = "1w09rqjlf27q65bzmq45m9ya3pw7igac6kbq4zpgpbdigfr9lzmq";
    };

    casualjim.gotemplate = vscode-utils.extensionFromVscodeMarketplace {
      name = "gotemplate";
      publisher = "casualjim";
      version = "0.4.0";
      sha256 = "0r6219f4gkpic3jjgj1666bwlfpvggf8wrgxp81v38bn9lmydn9g";
    };

    dorzey.vscode-sqlfluff = vscode-utils.extensionFromVscodeMarketplace {
      name = "vscode-sqlfluff";
      publisher = "dorzey";
      version = "2.4.4";
      sha256 = "1vlh8jazpzc0a8zziyn4n2ifbkjn16r3hcw30d25x41p2n45nkg3";
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
      version = "0.2.32";
      sha256 = "1rf3xpcfdj8vhd7s6nnd6a4r98mr7iz7b7fpk613gvjd6g0jgdw4";
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
