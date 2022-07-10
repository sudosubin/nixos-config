{
  description = "sudosubin/python310-with-extra-deps";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let pkgs = import nixpkgs { inherit system; }; in
      {
        devShell = pkgs.mkShell rec {
          venvDir = "./.venv";

          buildInputs = with pkgs; [
            # python
            poetry
            python310
            python310Packages.venvShellHook
            rdkafka # confluent-kafka
            libffi # cffi
            libmysqlclient # mysqlclient
            cyrus_sasl # python-ldap
            openldap # python-ldap
            expat # uwsgi

            # etc
            pre-commit
          ] ++ pkgs.lib.optionals pkgs.stdenv.isDarwin [
            darwin.apple_sdk.frameworks.IOKit # psutil
          ];

          postShellHook = ''
            if [ -f .pre-commit-config.yaml ] && [ ! -f .git/hooks/pre-commit ]; then
              ${pkgs.pre-commit}/bin/pre-commit install
            fi
          '';
        };
      }
    );
}
