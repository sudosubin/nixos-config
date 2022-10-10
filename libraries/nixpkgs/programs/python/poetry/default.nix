self: super:

let
  inherit (super.pkgs) lib;
  inherit (super.pkgs.stdenvNoCC.hostPlatform) isAarch64 isDarwin;

in
super.poetry.overridePythonAttrs (attrs: {
  preCheck = lib.optionalString (isDarwin && isAarch64) ''
    export no_proxy='*';
  '';

  postCheck = lib.optionalString (isDarwin && isAarch64) ''
    unset no_proxy
  '';
})
