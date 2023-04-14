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

    castwide.solargraph = vscode-utils.extensionFromVscodeMarketplace {
      name = "solargraph";
      publisher = "castwide";
      version = "0.24.0";
      sha256 = "0pcd4gwzg4rla5mz6kj4dqq30pyvsv6290an15yr89wxwcvk6qzf";
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
      version = "2.2.7";
      sha256 = "0gl9k3cp9gh9m8wp97pr4qwvz62pvw862z0d1xhww5344m3l7r1b";
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
      version = "0.2.26";
      sha256 = "1br0vr4v1xcl4c7bcqwzfqd4xr6q2ajwkipqrwm928mj96dkafkn";
    };

    hashicorp.hcl = vscode-utils.extensionFromVscodeMarketplace {
      name = "hcl";
      publisher = "hashicorp";
      version = "0.3.2";
      sha256 = "0snjivxdhr3s0lqarrzdzkv2f4qv28plbr3s9zpx7nqqfs97f4bk";
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

    nimsaem.nimvscode = vscode-utils.extensionFromVscodeMarketplace {
      name = "nimvscode";
      publisher = "nimsaem";
      version = "0.1.26";
      sha256 = "0aiaid81wx0vp340mz5pdyfi25pvvrfizdsiflrcnwbn0jfmqz5s";
    };

    phgn.vscode-starlark = vscode-utils.extensionFromVscodeMarketplace {
      name = "vscode-starlark";
      publisher = "phgn";
      version = "0.3.1";
      sha256 = "0xl8kff93wxb5x9vp4krkyfg542h9r3249sy7wp7vc95d9k1zkql";
    };

    rust-lang.rust = vscode-utils.extensionFromVscodeMarketplace {
      name = "rust";
      publisher = "rust-lang";
      version = "0.7.9";
      sha256 = "0asmr7c9jmik1047n359s9zmv2m7d0i8sixki4p02z7qzyrpxrfs";
    };

    shopify.ruby-lsp = vscode-utils.extensionFromVscodeMarketplace {
      name = "ruby-lsp";
      publisher = "Shopify";
      version = "0.2.4";
      sha256 = "06qxppdhih936r52w8sf468jl3vhrivgrcgsjpybxsnnlz46pk04";
    };
  };
}
