{ config, pkgs, inputs, ... }:

{
  nixpkgs.overlays = [
    (import ./programs/apple-cursor-theme.nix)
    (import ./programs/google-chrome.nix)
    (import ./programs/ll.nix)
    (import ./programs/pretendard.nix)
    (import ./programs/vscode.nix)
    (import ./programs/zpl-open.nix)
  ];
}
