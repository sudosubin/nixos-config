{ ... }:

{
  nixpkgs.overlays = [
    (import ./generators/xml.nix)

    (import ./programs/apple-cursor-theme)
    (import ./programs/figma-font-helper)
    (import ./programs/google-chrome)
    (import ./programs/jetbrains)
    (import ./programs/pass-securid)
    (import ./programs/pretendard)
    (import ./programs/pyopenssl)
    (import ./programs/vscode-extensions)
    (import ./programs/vscodium)
    (import ./programs/yabai)
    (import ./programs/zpl-open)
  ];
}
