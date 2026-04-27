{ inputs }:
with inputs;

let
  inherit (nixpkgs.lib) genAttrs platforms;
  forAllSystems = f: genAttrs platforms.all (system: f (import nixpkgs { inherit system; }));

in
{
  checks = forAllSystems (pkgs: {
    lefthook-check = lefthook.lib.${pkgs.stdenv.hostPlatform.system}.run {
      src = ./.;
      config = {
        pre-commit.commands = {
          nixfmt = {
            run = "${pkgs.lib.getExe pkgs.nixfmt} {staged_files}";
            glob = "*.nix";
          };
        };
      };
    };
  });

  devShells = forAllSystems (pkgs: {
    default =
      let
        inherit (pkgs.stdenvNoCC.hostPlatform) system isLinux isDarwin;
      in
      pkgs.mkShell {
        inputsFrom = [ self.checks.${system}.lefthook-check ];

        packages = pkgs.lib.optionals (isLinux || isDarwin) [
          pkgs.gh
        ];

        shellHook = ''
          export GITHUB_TOKEN="''${GITHUB_TOKEN:-$(gh auth token 2>/dev/null || true)}"
        '';
      };
  });

  formatter = forAllSystems (pkgs: pkgs.nixfmt);
}
