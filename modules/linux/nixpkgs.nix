{ ... }:

{
  nixpkgs.config.allowUnfree = true;
  nixpkgs.overlays = [
    (import ../shared/overlays/ll.nix)
    (import ../shared/overlays/pretendard.nix)
    (import ../shared/overlays/vscode.nix)

    (import ../linux/overlays/apple-cursor-theme.nix)
    (import ../linux/overlays/google-chrome.nix)
    (import ../linux/overlays/zpl-open.nix)
  ];
}
