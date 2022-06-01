final: { lib, fetchzip, stdenv, ... }@prev:

{
  python39 = prev.python39.override {
    packageOverrides = self: super: {
      inherit (import ./pyopenssl self super) pyopenssl;
    };
  };
}
