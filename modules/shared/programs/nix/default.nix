{
  pkgs,
  lib,
  config,
  ...
}:

{
  home.sessionVariables = {
    NIX_ACTIVATE_ROOT = "${config.home.homeDirectory}/Code/github.com/sudosubin/nixos-flakes";
  };

  home.packages = with pkgs; [
    nil
    nixfmt-rfc-style
    nixVersions.stable
    nix-activate
  ];
}
