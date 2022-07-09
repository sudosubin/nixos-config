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
      version = "1.0.1";
      sha256 = "1bjx46v17d18c9bplz70dx6fpsc6pr371ihpawhlr1y61b59n5aj";
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
      version = "0.0.5";
      sha256 = "14zyz4gjwvia1sl32zv758havjhgp8yz5xjcga7w3ix9kdm0irhs";
    };

    exiasr.hadolint = vscode-utils.extensionFromVscodeMarketplace {
      name = "hadolint";
      publisher = "exiasr";
      version = "1.1.1";
      sha256 = "0ls604nkahasny0kzh7677nr7mk9akcnljf4g41j0k47avza1hig";
    };

    flowtype.flow-for-vscode = vscode-utils.extensionFromVscodeMarketplace {
      name = "flow-for-vscode";
      publisher = "flowtype";
      version = "2.1.0";
      sha256 = "050wrjicwsn5ky490rpqnlq5m7q3y1h6k4ckrivxxpwmy8scfiak";
    };

    fwcd.kotlin = vscode-utils.extensionFromVscodeMarketplace {
      name = "kotlin";
      publisher = "fwcd";
      version = "0.2.26";
      sha256 = "1br0vr4v1xcl4c7bcqwzfqd4xr6q2ajwkipqrwm928mj96dkafkn";
    };

    hashicorp.hcl = vscode-utils.extensionFromVscodeMarketplace {
      name = "hcl";
      publisher = "hashicorp";
      version = "0.2.1";
      sha256 = "15ydllrridf1kc7867h0r7ykc2mnn5d94d1nvklzx0nnkq64pl75";
    };

    kevinrose.vsc-python-indent = vscode-utils.extensionFromVscodeMarketplace {
      name = "vsc-python-indent";
      publisher = "kevinrose";
      version = "1.17.0";
      sha256 = "14vf5p7pn2zgi4lhp6vkndclcxlw3lfdz0immi05gjyx20gp69i1";
    };

    nimsaem.nimvscode = vscode-utils.extensionFromVscodeMarketplace {
      name = "nimvscode";
      publisher = "nimsaem";
      version = "0.1.26";
      sha256 = "0aiaid81wx0vp340mz5pdyfi25pvvrfizdsiflrcnwbn0jfmqz5s";
    };

    rust-lang.rust = vscode-utils.extensionFromVscodeMarketplace {
      name = "rust";
      publisher = "rust-lang";
      version = "0.7.8";
      sha256 = "039ns854v1k4jb9xqknrjkj8lf62nfcpfn0716ancmjc4f0xlzb3";
    };
  };
}
