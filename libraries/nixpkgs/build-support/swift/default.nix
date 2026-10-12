{ callPackage }:

{
  fetchSwiftpmDeps = callPackage ./fetch-swiftpm-deps.nix { };
  buildSwiftPackage = callPackage ./build-swift-package.nix { };
  inherit (callPackage ./hooks { }) swiftpmSetupHook swiftAppBundleHook;
}
