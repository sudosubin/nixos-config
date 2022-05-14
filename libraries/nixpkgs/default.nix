{ ... }:

{
  nixpkgs.overlays = [
    (import ./generators/xml.nix)

    (import ./programs/apple-cursor-theme.nix)
    (import ./programs/figma-font-helper)
    (import ./programs/google-chrome.nix)
    (import ./programs/jetbrains.nix)
    (import ./programs/pass-securid.nix)
    (import ./programs/pretendard.nix)
    (import ./programs/pyopenssl.nix)
    (import ./programs/vscode-extensions.nix)
    (import ./programs/vscodium.nix)
    (import ./programs/yabai.nix)
    (import ./programs/zpl-open.nix)
  ];
}
