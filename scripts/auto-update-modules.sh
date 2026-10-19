#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(realpath "$(dirname "$0")/..")"
PACKAGES_DIR="$ROOT_DIR/libraries/nixpkgs/programs"
LOG_FILE="$(mktemp)"

trap 'rm -f "$ROOT_DIR/default.nix" "$ROOT_DIR/shell.nix" "$LOG_FILE"' EXIT

nixpkgs="$(REPO_ROOT="$ROOT_DIR" nix eval --raw --impure --expr '(builtins.getFlake (builtins.getEnv "REPO_ROOT")).inputs.nixpkgs.outPath')"
export NIX_PATH="nixpkgs=$nixpkgs${NIX_PATH:+:$NIX_PATH}"

cat > "$ROOT_DIR/default.nix" <<EOF
{}:
let
  overlay = final: prev:
    let
      localPackages = {
        $(for dir in "$PACKAGES_DIR"/*/default.nix "$PACKAGES_DIR"/pi-extensions/*/default.nix; do
          [ -f "$dir" ] || continue
          pkg="${dir#"$PACKAGES_DIR"/}"
          pkg="${pkg%/default.nix}"
          attr="${pkg//\//-}"
          echo "$attr = final.callPackage $PACKAGES_DIR/$pkg { };"
        done)
      };
    in
    localPackages // {
      inherit (final.callPackages $ROOT_DIR/libraries/nixpkgs/build-support/swift { })
        buildSwiftPackage fetchSwiftpmDeps swiftAppBundleHook swiftpmSetupHook;
      __localUpdates = localPackages // { recurseForDerivations = true; };
    };
in
import <nixpkgs> {
  overlays = [ overlay ];
}
EOF

# update.py runs package scripts through this shell in the repository root.
cat > "$ROOT_DIR/shell.nix" <<EOF
{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShell { buildInputs = []; }
EOF

status=0
nix-shell "$nixpkgs/maintainers/scripts/update.nix" \
  --arg include-overlays "(import $ROOT_DIR/default.nix { }).overlays" \
  --argstr path __localUpdates \
  --argstr keep-going true \
  --argstr skip-prompt true 2>&1 | tee "$LOG_FILE" || status=$?

if grep -qE ' - .+: ERROR$' "$LOG_FILE"; then
  echo "One or more package updates failed." >&2
  exit 1
fi

exit "$status"
