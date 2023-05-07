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
        sha256 = "sha256-zyO5BXP3HZ9wN05qybf2BNSf7uxj9scHxiIyIBABAgk=";
      })
    ];
  };

in
nixpkgs.lib.fix (self: (import "${src}/flake.nix").outputs { inherit self nixpkgs; })
