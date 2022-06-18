{ ... }:

{
  nixpkgs.overlays = [
    (import ./generators/xml.nix)

    (import ./programs/apple-cursor-theme)
    (import ./programs/aws-vault)
    (import ./programs/awscli2)
    (import ./programs/figma-font-helper)
    (import ./programs/google-chrome)
    (import ./programs/pass-securid)
    (import ./programs/python)
    (import ./programs/vscode-extensions)
    (import ./programs/yabai)
    (import ./programs/zpl-open)
  ];
}
