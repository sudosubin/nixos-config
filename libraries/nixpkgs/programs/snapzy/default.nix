{
  apple-sdk_26,
  buildSwiftPackage,
  fetchFromGitHub,
  fetchSwiftpmDeps,
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
  swiftpmDeps = fetchSwiftpmDeps {
    inherit (finalAttrs)
      pname
      version
      src
      swiftpmManifest
      swiftpmResolved
      ;
    hash = "sha256-m63K6TLbqeAmLNGv+lRtTV8HxDZDaqHQ1r/6neW7clM=";
    # SnapzyCLIKit is a local package with no checkout; swiftpmUnpackHook adds it back from the manifest
    preInstall = ''
      jq '.object.dependencies |= map(select(.packageRef.kind != "fileSystem"))' \
        .build/workspace-state.json > workspace-state.json~
      mv workspace-state.json~ .build/workspace-state.json
    '';
  };

  patches = [
    ./fix-magnifier-edge-fill.patch
    ./fix-magnifier-pixel-alignment.patch
  ];

  # swift-build, the default since Swift 6.4, rejects the unsigned Sparkle.xcframework
  swiftpmFlags = [
    "--build-system"
    "native"
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
    # Packages/ holds SnapzyCLIKit, so swiftpmUnpackHook linked the vendored deps at Packages/Packages
    rm Packages/Packages
    mv "$swiftpmDeps"/Packages/* Packages/

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

  # SwiftUI's @State is a macro from the Xcode-only SwiftUIMacros plugin in the macOS 27 SDK
  preConfigure = ''
    export DEVELOPER_DIR=${apple-sdk_26} SDKROOT=${apple-sdk_26.sdkroot}
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
