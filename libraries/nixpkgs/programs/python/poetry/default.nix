self: super:

let
  inherit (super.pkgs) lib;
  inherit (super.pkgs.stdenvNoCC.hostPlatform) isDarwin;

in
super.poetry.overridePythonAttrs (attrs: {
  # TODO: https://github.com/NixOS/nixpkgs/pull/198143
  postPatch = lib.optionalString isDarwin ''
    substituteInPlace pyproject.toml \
      --replace 'crashtest = "^0.3.0"' 'crashtest = "*"' \
      --replace 'xattr = { version = "^0.9.7"' 'xattr = { version = "*"'
  '';
})
