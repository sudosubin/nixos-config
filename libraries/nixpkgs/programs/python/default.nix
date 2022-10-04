final: { lib, fetchzip, stdenv, ... }@prev:

{
  python310 = prev.python310.override {
    packageOverrides = self: super: {
      debugpy = (import ./debugpy self super);
      poetry = (import ./poetry self super);
      pyopenssl = (import ./pyopenssl self super);
    };
  };
}
