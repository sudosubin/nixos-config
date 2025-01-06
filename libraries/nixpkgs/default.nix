{ inputs, lib, pkgs, ... }:

let
  inherit (pkgs.stdenvNoCC.hostPlatform) isDarwin;

in
{
  nixpkgs.overlays = [
    inputs.nix-vscode-extensions.overlays.default
    (import ./programs/google-chrome)
    (import ./programs/python)

    (final: prev: {
      apple-cursor-theme = final.callPackage ./programs/apple-cursor-theme { };
      cleanshot = final.callPackage ./programs/cleanshot { };
      clop = final.callPackage ./programs/clop { };
      deskpad = final.callPackage ./programs/deskpad { };
      git-spr = final.callPackage ./programs/git-spr { };
      hammerspoon = final.callPackage ./programs/hammerspoon { };
      homerow = final.callPackage ./programs/homerow { };
      ijhttp = final.callPackage ./programs/ijhttp { };
      orbstack = final.callPackage ./programs/orbstack { };
      pragmatapro = final.callPackage ./programs/pragmatapro { };
      redisinsight = final.callPackage ./programs/redisinsight { };
      vimPlugins = prev.vimPlugins // {
        github-nvim-theme = final.callPackage ./programs/vim-plugins/github-nvim-theme { };
      };
      zpl-open = final.callPackage ./programs/zpl-open { };
    })
  ];

  nixpkgs.config.allowUnfreePredicate = (pkg: builtins.elem (lib.getName pkg) [
    "1password"
    "1password-cli"
    "datagrip"
    "discord"
    "google-chrome"
    "homerow"
    "ijhttp"
    "ngrok"
    "orbstack"
    "raycast"
    "redisinsight"
    "cleanshot"
    "slack"
    "vscode-extension-github-copilot"
    "vscode-extension-github-copilot-chat"
    "vscode-extension-ms-vscode-remote-remote-ssh"
  ]);

  nixpkgs.config.permittedInsecurePackages = [
    "figma-linux-0.10.0"
  ];
}
