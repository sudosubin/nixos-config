{ inputs, ... }:
with inputs;

let
  pkgs = nixpkgs.legacyPackages."aarch64-darwin";

  src = pkgs.applyPatches {
    name = "nix-darwin";
    src = inputs.darwin;
    patches = [
      (pkgs.fetchpatch {
        url = "https://github.com/LnL7/nix-darwin/pull/619.patch";
        sha256 = "0y690rhq74k90f63c06hr02gifmw390n4l22zgsjxgvfrggv61qc";
      })
    ];
  };

in
nixpkgs.lib.fix (self: (import "${src}/flake.nix").outputs { inherit self nixpkgs; })
