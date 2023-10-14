self: super:

super.cherrypy.overridePythonAttrs (attrs: with super; {
  disabledTests = (attrs.disabledTests or [ ]) ++ lib.optionals stdenv.isDarwin [
    "test_0_Session"
  ];
})
