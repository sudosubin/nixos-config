{
  description = "sudosubin/node16-yarn";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let pkgs = import nixpkgs { inherit system; }; in
      {
        devShell = pkgs.mkShell rec {
          buildInputs = with pkgs; [
            # node
            nodejs-16_x
            yarn
          ];
        };
      }
    );
}
