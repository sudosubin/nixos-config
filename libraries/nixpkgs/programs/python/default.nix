final: { lib, fetchzip, stdenv, ... }@prev:

{
  python310 = prev.python310.override {
    packageOverrides = self: super: {
      inherit (import ./pyopenssl self super) pyopenssl;
      inherit (import ./skia-pathops self super) skia-pathops;
      inherit (import ./uharfbuzz self super) uharfbuzz;
    };
  };
}
