self: super: {
  pyopenssl = super.pyopenssl.overridePythonAttrs (attrs: {
    meta.broken = false;
  });
}
