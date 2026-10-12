{
  lib,
  actool,
  jq,
  makeSetupHook,
  perl,
  python3Packages,
  rcodesign,
  writers,
}:

{
  swiftpmSetupHook = makeSetupHook {
    name = "swiftpm-setup-hook.sh";
    substitutions = {
      jq = lib.getExe jq;
      perl = lib.getExe perl;
    };
  } ./swiftpm-setup-hook.sh;

  swiftAppBundleHook = makeSetupHook {
    name = "swift-app-bundle-hook.sh";
    propagatedBuildInputs = [
      actool
      rcodesign
    ];
    substitutions = {
      swiftAppBundle = lib.getExe (
        writers.writePython3Bin "swift-app-bundle" {
          libraries = [ python3Packages.openstep-plist ];
          flakeIgnore = [ "E501" ];
        } (builtins.readFile ./swift-app-bundle.py)
      );
    };
  } ./swift-app-bundle-hook.sh;
}
