{
  buildSwiftPackage,
  fetchFromGitHub,
  lib,
  nix-update-script,
  swiftAppBundleHook,
}:

buildSwiftPackage (finalAttrs: {
  pname = "deskpad";
  version = "1.3.2";

  src = fetchFromGitHub {
    owner = "Stengo";
    repo = "DeskPad";
    tag = "v${finalAttrs.version}";
    hash = "sha256-loL/oyOR2yJNl/+zgaS/BSCQ6WQe7brJUm6lj2jkDY0=";
  };

  swiftpmManifest = ./Package.swift;
  swiftpmResolved = "DeskPad.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved";
  swiftpmDepsHash = "sha256-FwLnfeWmiNQJBtAiWjuiZIQF3T1+j57QyRC2RZTp7NY=";

  nativeBuildInputs = [ swiftAppBundleHook ];

  xcodeProject = "DeskPad.xcodeproj";
  appResources = [ "DeskPad/Assets.xcassets" ];

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--custom-dep"
      "swiftpmDeps"
    ];
  };

  meta = {
    description = "A virtual monitor for screen sharing";
    homepage = "https://github.com/Stengo/DeskPad";
    changelog = "https://github.com/Stengo/DeskPad/releases/tag/v${finalAttrs.version}";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.darwin;
    sourceProvenance = with lib.sourceTypes; [ fromSource ];
  };
})
