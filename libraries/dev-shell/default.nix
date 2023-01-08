{ inputs, ... }:
with inputs;

flake-utils.lib.eachDefaultSystem (system:
let
  pkgs = nixpkgs.legacyPackages.${system};

in
{
  checks = {
    pre-commit-check = pre-commit-hooks.lib.${system}.run {
      src = ../.;
      hooks = {
        nixpkgs-fmt.enable = true;
      };
    };
  };
  devShell = pkgs.mkShell {
    buildInputs = with pkgs; [ pre-commit ];
    inherit (self.checks.${system}.pre-commit-check) shellHook;
  };
})
