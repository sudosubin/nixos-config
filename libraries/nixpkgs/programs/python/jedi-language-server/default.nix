self: super:

super.jedi-language-server.overridePythonAttrs (attrs: {
  propagatedBuildInputs = attrs.propagatedBuildInputs ++ (with self; [
    pydantic
    lsprotocol
  ]);
})
