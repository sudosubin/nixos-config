{ inputs, ... }:
with inputs;

flake-utils.lib.eachDefaultSystem (
  system:
  let
    pkgs = nixpkgs.legacyPackages.${system};

  in
  {
    apps = {
      format = flake-utils.lib.mkApp { drv = pkgs.nixfmt-rfc-style; };
    };
    checks = {
      lefthook-check = lefthook.lib.${system}.run {
        src = ./.;
        config = {
          pre-commit.commands = {
            nixfmt = {
              run = "${pkgs.nixfmt-rfc-style}/bin/nixfmt {staged_files}";
              glob = "*.nix";
            };
          };
        };
      };
    };
    devShell = nixpkgs.legacyPackages.${system}.mkShell {
      inherit (self.checks.${system}.lefthook-check) shellHook;
    };
  }
)
