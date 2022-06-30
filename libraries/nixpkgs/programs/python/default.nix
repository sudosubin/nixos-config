final: { lib, fetchzip, stdenv, ... }@prev:

{
  python310 = prev.python310.override {
    packageOverrides = self: super: {
      inherit (import ./fonttools self super) fonttools;
      inherit (import ./pyopenssl self super) pyopenssl;
    };
  };
}
