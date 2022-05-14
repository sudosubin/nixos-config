final: { lib, fetchzip, stdenv, ... }@prev:

{
  python39 = prev.python39.override {
    packageOverrides = self: super: {
      pyopenssl = super.pyopenssl.overridePythonAttrs (attrs: {
        meta.broken = false;
      });
    };
  };
}
