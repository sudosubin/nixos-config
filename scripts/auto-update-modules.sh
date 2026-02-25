#!/usr/bin/env bash
set -eEuo pipefail

ROOT_DIR="$(readlink --canonicalize -- "$(dirname -- "$0")/..")"
PACKAGES_DIR="$ROOT_DIR/libraries/nixpkgs/programs"

# Mock nixpkgs and shell.nix
trap 'rm -f "$ROOT_DIR/default.nix" "$ROOT_DIR/shell.nix"' ERR EXIT

# Create temporary default.nix
cat > "$ROOT_DIR/default.nix" <<EOF
{}: import <nixpkgs> {
  overlays = [
    (final: prev: {
      $(cd "$PACKAGES_DIR" && for dir in */default.nix pi-extensions/*/default.nix vscode-extensions/*/default.nix; do
        [ -f "$dir" ] || continue
        pkg="${dir%/default.nix}"
        attr="${pkg//\//-}"
        echo "$attr = final.callPackage $PACKAGES_DIR/$pkg { };"
      done)
    })
  ];
}
EOF

# Create temporary shell.nix as a proper derivation
cat > "$ROOT_DIR/shell.nix" <<EOF
{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShell { buildInputs = []; }
EOF

# Run update scripts
nixpkgs="$(nix-instantiate --eval --expr "<nixpkgs>")"
nix-shell "$nixpkgs/maintainers/scripts/update.nix" \
  --arg include-overlays "(import $ROOT_DIR/default.nix { }).overlays" \
  --arg get-script "(
    let prefix = \"$PACKAGES_DIR/\"; prefixLen = builtins.stringLength prefix;
    in (p:
      if (builtins.substring 0 prefixLen (p.meta.position or \"\")) == prefix then
        p.updateScript or null
      else
        null)
  )" \
  --argstr keep-going true \
  --arg predicate "(
    let prefix = \"$PACKAGES_DIR/\"; prefixLen = builtins.stringLength prefix;
    in (_: p: (builtins.substring 0 prefixLen (p.meta.position or \"\")) == prefix)
  )" \
  --argstr skip-prompt true
