{ callPackage }:

{
  buildSwiftPackage = callPackage ./build-swift-package.nix { };
  inherit (callPackage ./hooks { }) swiftpmSetupHook swiftAppBundleHook;
}
