{ config, pkgs, inputs, ... }:

{
  nixpkgs.overlays = [
    (import ./programs/apple-cursor-theme.nix)
    (import ./programs/google-chrome.nix)
    (import ./programs/pass-securid.nix)
    (import ./programs/pretendard.nix)
    (import ./programs/vscode-extensions.nix)
    (import ./programs/zpl-open.nix)
  ];
}
