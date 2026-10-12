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
  version = "2.0.0";

  src = fetchFromGitHub {
    owner = "duongductrong";
    repo = "Snapzy";
    tag = "v${finalAttrs.version}";
    hash = "sha256-nPr+PYDx6v5o4PaIel7OsMhRXIfRYFOT4zqdQrUq9Ko=";
  };

  swiftpmManifest = ./Package.swift;
  swiftpmResolved = "Snapzy.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved";
  swiftpmDepsHash = "sha256-yxxEU9nC5T7NbJf3HLFYN5DlxOBWVKUJXxxIMNQk+W4=";

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

    # Work around a swiftc 6.2.4 segfault in implicit deinits of generic classes
    substituteInPlace Snapzy/Services/Cloud/S3MultipartUploader.swift --replace-fail \
      "class ThreadSafeDictionary<Key: Hashable, Value>: @unchecked Sendable {" \
      "class ThreadSafeDictionary<Key: Hashable, Value>: @unchecked Sendable { @inline(never) deinit {}"
    substituteInPlace Snapzy/Features/Capture/CaptureDelayCountdownController.swift --replace-fail \
      "class FirstMouseHostingView<Content: View>: NSHostingView<Content> {" \
      "class FirstMouseHostingView<Content: View>: NSHostingView<Content> { @inline(never) deinit {}"
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

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--version-regex"
      "^v(\\d+\\.\\d+\\.\\d+)$"
      "--custom-dep"
      "swiftpmDeps"
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
