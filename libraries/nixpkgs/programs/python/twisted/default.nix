self: super: {
  twisted = super.twisted.overridePythonAttrs (attrs: {
    checkPhase = "";
  });
}
