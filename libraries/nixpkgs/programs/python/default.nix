final: { lib, fetchzip, stdenv, ... }@prev:

{
  python310 = prev.python310.override {
    packageOverrides = self: super: {
      inherit (import ./pyopenssl self super) pyopenssl;
    };
  };
}
