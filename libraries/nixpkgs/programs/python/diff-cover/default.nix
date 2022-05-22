self: super: {
  diff-cover = super.diff-cover.overridePythonAttrs (attrs: {
    doCheck = false;
  });
}
