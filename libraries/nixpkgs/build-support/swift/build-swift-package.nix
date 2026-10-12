{
  lib,
  stdenv,
  fetchSwiftpmDeps,
  swift,
  swiftpm,
  swiftpmSetupHook,
}:

# Build with dependencies vendored by fetchSwiftpmDeps:
# - swiftpmManifest: Package.swift to use in place of the source's own
# - swiftpmResolved: Package.resolved, relative to the source root
lib.extendMkDerivation {
  constructDrv = stdenv.mkDerivation;

  excludeDrvArgNames = [ "swiftpmDepsHash" ];

  extendDrvArgs =
    finalAttrs:
    {
      nativeBuildInputs ? [ ],
      ...
    }@args:
    {
      swiftpmDeps =
        args.swiftpmDeps or (fetchSwiftpmDeps (
          lib.getAttrs (lib.intersectLists [
            "pname"
            "version"
            "src"
            "swiftpmManifest"
            "swiftpmResolved"
          ] (lib.attrNames finalAttrs)) finalAttrs
          // {
            hash = args.swiftpmDepsHash;
          }
        ));

      nativeBuildInputs = nativeBuildInputs ++ [
        swiftpmSetupHook
        swift
        swiftpm
      ];

      strictDeps = true;

      __structuredAttrs = true;
    };
}
