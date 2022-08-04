final: { lib, fetchzip, stdenv, ... }@prev:

{
  python310 = prev.python310.override {
    packageOverrides = self: super: {
      inherit (import ./debugpy self super) debugpy;
      inherit (import ./pyopenssl self super) pyopenssl;
    };
  };
}
