{
  buildSwiftPackage,
  fetchFromGitHub,
  fetchNpmDeps,
  lib,
  nix-update-script,
  nodejs,
  npmHooks,
  sqlite,
  swiftAppBundleHook,
}:

buildSwiftPackage (finalAttrs: {
  pname = "hammerspoon2";
  version = "0.0.16";

  src = fetchFromGitHub {
    owner = "cmsj";
    repo = "Hammerspoon2";
    tag = finalAttrs.version;
    hash = "sha256-ZACwWGtvYiUKDGmuTPLaH4lNHldb3oiKNJdqWkGEHLw=";
  };

  swiftpmManifest = ./Package.swift;
  swiftpmResolved = "Hammerspoon 2.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved";
  swiftpmDepsHash = "sha256-9p55ymAtYaf7zPmu7ADVDl8znqktKhs+kh4QopA2YPk=";

  npmDeps = fetchNpmDeps {
    inherit (finalAttrs) src;
    hash = "sha256-Vx9TS6PJAWHcSg4IQTZ0FeiwDoMwH6LZzi9tEpbjXCI=";
  };

  nativeBuildInputs = [
    nodejs
    npmHooks.npmConfigHook
    swiftAppBundleHook
  ];

  buildInputs = [ sqlite ];

  postPatch = ''
    # SQLite is already exposed by Bridging-Header.h; avoid the SDK's broken module map.
    substituteInPlace "Hammerspoon 2/Modules/node/NodeModuleSQLite.swift" \
      --replace-fail "import SQLite3" ""

    # Sources Xcode compiles into more than one target
    cp HammerspoonOSAScriptHelper/HSOSAScriptShared.swift "Hammerspoon 2/"
    cp "Hammerspoon 2/Utilities/LoggingLevels.swift" hs2/
    cp HammerspoonIPCBroker/HSIPCShared.swift "Hammerspoon 2/"
    cp HammerspoonIPCBroker/HSIPCShared.swift hs2/

    # MapKit's geocoding requests are not Sendable in the macOS 26.5 SDK
    substituteInPlace "Hammerspoon 2/Modules/hs.location/HSLocationGeocoder.swift" \
      --replace-fail "import MapKit" "@preconcurrency import MapKit"

    # @diagnose requires a newer Swift compiler than the pinned nixpkgs provides.
    for file in "Hammerspoon 2/Modules/hs.sharing/HSSharingModule.swift" \
      "Hammerspoon 2/Modules/hs.urlevent/HSURLEventModule.swift"; do
      substituteInPlace "$file" \
        --replace-fail '@diagnose(DeprecatedDeclaration, as: ignored, reason: "No suitable replacement exists")' ""
    done

    substituteInPlace scripts/extract-docs.js \
      --replace-fail "new Date().toISOString()" "new Date(process.env.SOURCE_DATE_EPOCH * 1000).toISOString()"
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
    install -Dm755 "$bin/HammerspoonIPCBroker" "$app/Contents/MacOS/HammerspoonIPCBroker"
    install -Dm644 LaunchAgents/net.tenshu.Hammerspoon-2.HammerspoonIPCBroker.plist \
      "$app/Contents/Library/LaunchAgents/net.tenshu.Hammerspoon-2.HammerspoonIPCBroker.plist"

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
