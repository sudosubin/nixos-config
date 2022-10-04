self: super:
let
  inherit (super.pkgs) lib stdenvNoCC;

in
super.poetry.overridePythonAttrs (attrs: {
  preCheck = lib.optionalString (stdenvNoCC.isDarwin && stdenvNoCC.isAarch64) ''
    export no_proxy='*';
  '';

  postCheck = lib.optionalString (stdenvNoCC.isDarwin && stdenvNoCC.isAarch64) ''
    unset no_proxy
  '';
})
