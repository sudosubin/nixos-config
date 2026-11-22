{
  lib,
  stdenv,
  apple-sdk_26,
  fetchSwiftPMDeps,
  swift,
  swiftpm,
  swiftpmSetupHook,
}:

lib.extendMkDerivation {
  constructDrv = stdenv.mkDerivation;

  excludeDrvArgNames = [
    "swiftpmDepsHash"
    "swiftpmExcludedPins"
  ];

  extendDrvArgs =
    finalAttrs:
    {
      nativeBuildInputs ? [ ],
      passthru ? { },
      swiftpmResolved ? "Package.resolved",
      # fetchSwiftPMDeps fetches every pin, including ones the manifest does not use
      swiftpmExcludedPins ? [ ],
      # nixpkgs' swift-build cannot verify xcframeworks (sigtool) and links without an SDK version
      swiftpmBuildSystem ? "native",
      # SwiftUI's @State is a macro from the Xcode-only SwiftUIMacros plugin in the macOS 27 SDK
      swiftpmSdk ? apple-sdk_26,
      ...
    }@args:
    {
      swiftpmDeps =
        args.swiftpmDeps or (fetchSwiftPMDeps {
          inherit (finalAttrs) pname version src;
          hash = args.swiftpmDepsHash;
          postPatch =
            if swiftpmExcludedPins != [ ] then
              ''
                jq --argjson excluded ${lib.escapeShellArg (builtins.toJSON swiftpmExcludedPins)} \
                  '.pins |= map(select(.identity as $id | $excluded | index($id) | not))' \
                  ${lib.escapeShellArg swiftpmResolved} > Package.resolved~
                mv Package.resolved~ Package.resolved
              ''
            else
              lib.optionalString (swiftpmResolved != "Package.resolved") ''
                cp ${lib.escapeShellArg swiftpmResolved} Package.resolved
              '';
        });

      inherit swiftpmBuildSystem swiftpmSdk;

      nativeBuildInputs = nativeBuildInputs ++ [
        swiftpmSetupHook
        swift
        swiftpm
      ];

      # For nix-update's --custom-dep
      passthru =
        lib.optionalAttrs (finalAttrs.swiftpmDeps != null) {
          swiftpmVendor = finalAttrs.swiftpmDeps.vendorStaging;
        }
        // passthru;

      strictDeps = true;

      __structuredAttrs = true;
    };
}
