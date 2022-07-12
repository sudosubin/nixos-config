{
  description = "sudosubin/python310-with-extra-deps";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system overlays; };
        overlays = [
          (final: prev: {
            openldap = prev.openldap.overrideAttrs (attrs: {
              postInstall = ''
                ${attrs.postInstall or ""}
                ln -s $out/lib/libldap.la $out/lib/libldap_r.la
                ln -s $out/lib/libldap.dylib $out/lib/libldap_r.dylib
                ln -s $out/lib/libldap.2.dylib $out/lib/libldap_r.2.dylib
              '';
            });
          })
        ];


      in
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
