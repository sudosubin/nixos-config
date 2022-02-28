{ config, pkgs, ... }:

let
  nix-activate = pkgs.writeShellScriptBin "nix-activate" ''
    set -euo pipefail

    CURRENT_DIR="$(pwd)"
    if [ -f "$CURRENT_DIR/flake.nix" ]; then
      echo "use flake ." > .envrc
      exit 0
    fi

    NAME="$(basename $(dirname $CURRENT_DIR))/$(basename $CURRENT_DIR)"
    NIX_ACTIVATE_ROOT="''${NIX_ACTIVATE_ROOT:-~/Code/sudosubin/nixos-flakes}"

    echo "use flake $NIX_ACTIVATE_ROOT/$NAME" > .envrc
  '';
in
{
  home.packages = with pkgs; [
    rnix-lsp
    nixpkgs-fmt
    nix-activate
  ];
}
