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
        sha256 = "03ykb7dsay8lv7pncyhdzwlwrqvdwc5i21dvrv5bxhlnf6rl4rfp";
      })
    ];
  };

in
nixpkgs.lib.fix (self: (import "${src}/flake.nix").outputs { inherit self nixpkgs; })
