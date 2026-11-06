{ pkgs, ... }:

{
  programs.vscodium = rec {
    enable = true;
    package = pkgs.vscodium;
    argvSettings.enable-crash-reporter = false;
    profiles.default = {
      extensions =
        (with (pkgs.forVSCodeVersion package.vscodeVersion).open-vsx; [
          adguard.adblock
          anthropic.claude-code
          arcanis.vscode-zipfs
          astral-sh.ty
          biomejs.biome
          bradlc.vscode-tailwindcss
          bufbuild.vscode-buf
          charliermarsh.ruff
          davidanson.vscode-markdownlint
          dbaeumer.vscode-eslint
          denoland.vscode-deno
          esbenp.prettier-vscode
          foxundermoon.shell-format
          fwcd.kotlin
          github.github-vscode-theme
          golang.go
          graphql.vscode-graphql
          graphql.vscode-graphql-syntax
          hashicorp.terraform
          jnoortheen.nix-ide
          ms-pyright.pyright
          ms-python.debugpy
          ms-python.python
          oxc.oxc-vscode
          pkief.material-product-icons
          prisma.prisma
          redhat.java
          redhat.vscode-yaml
          rust-lang.rust-analyzer
          samuelcolvin.jinjahtml
          shardulm94.trailing-spaces
          tamasfe.even-better-toml
          teticio.python-envy
          timonwong.shellcheck
          usernamehw.errorlens
          yoavbls.pretty-ts-errors
          yzhang.markdown-all-in-one
        ])
        ++ (with (pkgs.forVSCodeVersion package.vscodeVersion).open-vsx-release; [
          eamodio.gitlens
        ])
        ++ (with (pkgs.forVSCodeVersion package.vscodeVersion).vscode-marketplace; [
          bierner.markdown-preview-github-styles
        ])
        ++ [
          (pkgs.open-vsx.pkief.material-icon-theme.override {
            settings = {
              hidesExplorerArrows = true;
              files.associations."*.gotmpl" = "template";
            };
          })
        ];
      userSettings = ./files/settings.json;
    };
  };

  home.shellAliases = {
    code = "codium";
  };
}
