self: super:

let
  inherit (super.pkgs) lib;
  inherit (super.pkgs.stdenvNoCC.hostPlatform) isDarwin;

in
super.cherrypy.overridePythonAttrs (attrs: {
  disabledTests = (attrs.disabledTests or [ ]) ++ [
    "test_xmlrpc"
  ];
})
