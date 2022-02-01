{ config, pkgs, ... }:

let
  nix-activate = pkgs.writeShellScriptBin "nix-activate" ''
    set -euo pipefail
    NAME=$(git remote get-url origin | sed 's/.*\:\(.*\/[^.]*\).*/\1/')
    NIX_ACTIVATE_ROOT="''${NIX_ACTIVATE_ROOT:-$HOME/Code/sudosubin/nixos-flakes}"
    nix develop path:$NIX_ACTIVATE_ROOT/$NAME --command $SHELL
  '';
in
{
  home.packages = [
    nix-activate
  ];
}
