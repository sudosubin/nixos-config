{
  buildSwiftPackage,
  fetchFromGitHub,
  lib,
  nix-update-script,
  sqlite,
  swiftAppBundleHook,
}:

buildSwiftPackage (finalAttrs: {
  pname = "snapzy";
  version = "2.2.0";

  src = fetchFromGitHub {
    owner = "duongductrong";
    repo = "Snapzy";
    tag = "v${finalAttrs.version}";
    hash = "sha256-8u7hYaQ4xM+SXJvqBE9Gpx8N/mGY1WFipcPxV2kaD7w=";
  };

  swiftpmManifest = ./Package.swift;
  swiftpmResolved = "Snapzy.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved";
  swiftpmDepsHash = "sha256-y/jODBgHT26UeSdYz+lTA41RYxZcjhh5LDdh/NgFWfM=";

  patches = [
    ./fix-magnifier-edge-fill.patch
    ./fix-magnifier-pixel-alignment.patch
  ];

  nativeBuildInputs = [ swiftAppBundleHook ];

  # GRDB requires SQLITE_ENABLE_SNAPSHOT
  buildInputs = [
    (sqlite.overrideAttrs (old: {
      env = old.env // {
        NIX_CFLAGS_COMPILE = old.env.NIX_CFLAGS_COMPILE + " -DSQLITE_ENABLE_SNAPSHOT";
      };
    }))
  ];

  postPatch = ''
    # SwiftPM compiles every file in a C target
    find Packages/libwebp-Xcode/libwebp/{src,sharpyuv} -type f ! -name "*.[ch]" -delete
  '';

  xcodeProject = "Snapzy.xcodeproj";
  appResources = [
    "Snapzy/Resources/Assets.xcassets"
    "Snapzy/Resources/Localization/*/*.xcstrings"
    "Snapzy/Resources/Localization/manifest.json"
    "Snapzy/Resources/*.lproj"
    "Snapzy/Resources/whats_new.json"
    "Snapzy/Resources/Wallpapers/*.jpg"
  ];

  postInstall = ''
    install -Dm755 "$(swiftpmBinPath)/SnapzyCLIMain" "$out/Applications/Snapzy.app/Contents/Helpers/snapzy"
  '';

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--use-github-releases"
      "--version-regex"
      "^v(\\d+\\.\\d+\\.\\d+)$"
      "--custom-dep"
      "swiftpmVendor"
    ];
  };

  meta = {
    description = "Open-source native macOS screenshot and screen recording app";
    homepage = "https://github.com/duongductrong/Snapzy";
    changelog = "https://github.com/duongductrong/Snapzy/releases/tag/v${finalAttrs.version}";
    license = lib.licenses.bsd3;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.darwin;
    sourceProvenance = with lib.sourceTypes; [
      fromSource
      binaryNativeCode
    ];
  };
})
