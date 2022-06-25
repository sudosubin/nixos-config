/**
  * Fix uharfbuzz on darwin
  * 1) https://github.com/NixOS/nixpkgs/pull/178359
  * 2) https://github.com/NixOS/nixpkgs/pull/178795
*/
self: super:
{
  uharfbuzz = super.uharfbuzz.overrideAttrs (attrs: {
    buildInputs = (attrs.buildInputs or [ ]) ++ super.pkgs.lib.optionals super.stdenv.isDarwin [
      super.pkgs.darwin.apple_sdk.frameworks.ApplicationServices
    ];

    meta.broken = false;
  });
}
