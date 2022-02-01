{ inputs, ... }:
with inputs;

flake-utils.lib.eachDefaultSystem (system: {
  checks = {
    pre-commit-check = pre-commit-hooks.lib.${system}.run {
      src = ./.;
      hooks = {
        nixpkgs-fmt.enable = true;
      };
    };
  };
  devShell = nixpkgs.legacyPackages.${system}.mkShell {
    inherit (self.checks.${system}.pre-commit-check) shellHook;
  };
})
