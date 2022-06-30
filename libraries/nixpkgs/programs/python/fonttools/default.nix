self: super:
let
  inherit (super.pkgs) lib;

in
{
  fonttools = super.fonttools.overridePythonAttrs (attrs: {
    checkInputs = with super; [ pytestCheckHook ]
      ++ lib.concatLists (lib.attrVals [ "woff" "interpolatable" "repacker" ] attrs.passthru.optional-dependencies);
  });
}
