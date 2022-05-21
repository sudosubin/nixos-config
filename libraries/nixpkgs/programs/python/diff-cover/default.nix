final: { lib, fetchzip, stdenv, ... }@prev:

{
  python39 = prev.python39.override {
    packageOverrides = self: super: {
      diff-cover = super.diff-cover.overridePythonAttrs (attrs: {
        doCheck = false;
      });
    };
  };
}
