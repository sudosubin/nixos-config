{ inputs, ... }:
with inputs;

let

  inherit (nixpkgs.lib) genAttrs platforms;
  forAllSystems = f: genAttrs platforms.all (system: f (import nixpkgs { inherit system; }));

in
{
  formatter = forAllSystems (pkgs: pkgs.nixfmt-rfc-style);

  checks = forAllSystems (pkgs: {
    lefthook-check = lefthook.lib.${pkgs.system}.run {
      src = ./.;
      config = {
        pre-commit.commands = {
          nixfmt = {
            run = "${pkgs.lib.getExe pkgs.nixfmt-rfc-style} {staged_files}";
            glob = "*.nix";
          };
        };
      };
    };
  });

  devShells = forAllSystems (pkgs: {
    default = pkgs.mkShell {
      inherit (self.checks.${pkgs.system}.lefthook-check) shellHook;
    };
  });
}
