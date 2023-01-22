{ inputs, ... }:
with inputs;

flake-utils.lib.eachDefaultSystem (system:
let
  pkgs = nixpkgs.legacyPackages.${system};

in
{
  apps = {
    format = flake-utils.lib.mkApp { drv = pkgs.nixpkgs-fmt; };
  };
  checks = {
    lefthook-check = lefthook.lib.${system}.run {
      src = ./.;
      config = {
        pre-commit.commands = {
          nixpkgs-fmt = {
            run = "${pkgs.nixpkgs-fmt}/bin/nixpkgs-fmt {staged_files}";
            glob = "*.nix";
          };
        };
      };
    };
  };
  devShell = nixpkgs.legacyPackages.${system}.mkShell {
    inherit (self.checks.${system}.lefthook-check) shellHook;
  };
})
