{
  buildSwiftPackage,
  fetchFromGitHub,
  fetchNpmDeps,
  lib,
  nix-update-script,
  nodejs,
  npmHooks,
  swiftAppBundleHook,
}:

buildSwiftPackage (finalAttrs: {
  pname = "hammerspoon2";
  version = "0.0.13";

  src = fetchFromGitHub {
    owner = "cmsj";
    repo = "Hammerspoon2";
    tag = finalAttrs.version;
    hash = "sha256-R4E+1acpLNEEi79Fs1Re1xBP/Ey5t2e/8GMz6y0a2Pg=";
  };

  swiftpmManifest = ./Package.swift;
  swiftpmResolved = "Hammerspoon 2.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved";
  swiftpmDepsHash = "sha256-9p55ymAtYaf7zPmu7ADVDl8znqktKhs+kh4QopA2YPk=";

  npmDeps = fetchNpmDeps {
    inherit (finalAttrs) src;
    hash = "sha256-nPoIYIjY9Sswx3CcxYRTwB617p1pM3EF2H+46hdwk/o=";
  };

  nativeBuildInputs = [
    nodejs
    npmHooks.npmConfigHook
    swiftAppBundleHook
  ];

  postPatch = ''
    # Sources Xcode compiles into more than one target
    cp HammerspoonOSAScriptHelper/HSOSAScriptShared.swift "Hammerspoon 2/"
    cp "Hammerspoon 2/Utilities/LoggingLevels.swift" hs2/

    # MapKit's geocoding requests are not Sendable in the macOS 26.5 SDK
    substituteInPlace "Hammerspoon 2/Modules/hs.location/HSLocationGeocoder.swift" \
      --replace-fail "import MapKit" "@preconcurrency import MapKit"
  '';

  preBuild = ''
    npm run docs:generate
  '';

  xcodeProject = "Hammerspoon 2.xcodeproj";
  appResources = [
    "Hammerspoon 2/Assets.xcassets"
    "Hammerspoon 2/Engine/*.js"
    "Hammerspoon 2/Modules/*/*.js"
    "DefaultConfig"
    "docs/api.json"
    "docs/hammerspoon.d.ts"
    "docs/js"
    "docs/ts"
  ];

  postInstall = ''
    app="$out/Applications/Hammerspoon 2.app"
    bin="$(swiftpmBinPath)"

    install -Dm755 "$bin/hs2" "$app/Contents/MacOS/hs2"

    xpc="$app/Contents/XPCServices/HammerspoonOSAScriptHelper.xpc/Contents"
    install -Dm755 "$bin/HammerspoonOSAScriptHelper" "$xpc/MacOS/HammerspoonOSAScriptHelper"
    cat > "$xpc/Info.plist" <<PLIST
    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0">
    <dict>
      <key>CFBundleDevelopmentRegion</key><string>en</string>
      <key>CFBundleDisplayName</key><string>HammerspoonOSAScriptHelper</string>
      <key>CFBundleExecutable</key><string>HammerspoonOSAScriptHelper</string>
      <key>CFBundleIdentifier</key><string>net.tenshu.Hammerspoon-2.HammerspoonOSAScriptHelper</string>
      <key>CFBundleInfoDictionaryVersion</key><string>6.0</string>
      <key>CFBundleName</key><string>HammerspoonOSAScriptHelper</string>
      <key>CFBundlePackageType</key><string>XPC!</string>
      <key>CFBundleShortVersionString</key><string>1.0</string>
      <key>CFBundleVersion</key><string>1</string>
      <key>LSMinimumSystemVersion</key><string>26.0</string>
      <key>LSUIElement</key><true/>
      <key>XPCService</key>
      <dict>
        <key>ServiceType</key><string>Application</string>
      </dict>
    </dict>
    </plist>
    PLIST
  '';

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--custom-dep"
      "swiftpmDeps"
    ];
  };

  meta = {
    description = "A modernized rewrite of Hammerspoon - a powerful macOS application for automating your Mac using JavaScript.";
    homepage = "https://github.com/cmsj/Hammerspoon2";
    changelog = "https://github.com/cmsj/Hammerspoon2/releases/tag/${finalAttrs.version}";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.darwin;
    sourceProvenance = with lib.sourceTypes; [
      fromSource
      binaryNativeCode
    ];
  };
})
