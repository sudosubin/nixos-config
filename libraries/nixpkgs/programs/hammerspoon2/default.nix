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
  version = "0.0.18";

  src = fetchFromGitHub {
    owner = "cmsj";
    repo = "Hammerspoon2";
    tag = finalAttrs.version;
    hash = "sha256-iVskJBpuslIMY8WmwK4iUZYZzdZbEcXsZuykxRtj3XQ=";
  };

  swiftpmManifest = ./Package.swift;
  swiftpmResolved = "Hammerspoon 2.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved";
  swiftpmDepsHash = "sha256-dG7fgRzUWMHGhfOtdtlkUwXZ8JlyYJOBw02e8gcO6bU=";
  # Xcode-only lint plugin, and its binary target is not an XCFramework
  swiftpmExcludedPins = [ "swiftlintplugins" ];

  npmDeps = fetchNpmDeps {
    inherit (finalAttrs) src;
    hash = "sha256-/UpOlZMg3pu6HgnTLdN11Rz+Zo+Or8Pzu9XmrJdPDBM=";
  };

  nativeBuildInputs = [
    nodejs
    npmHooks.npmConfigHook
    swiftAppBundleHook
  ];

  buildInputs = [ sqlite ];

  postPatch = ''
    # nixpkgs' SDK lacks the sqlite3.h its SQLite3 module map needs; Bridging-Header.h includes sqlite
    substituteInPlace "Hammerspoon 2/Modules/node/NodeModuleSQLite.swift" \
      --replace-fail "import SQLite3" ""

    # Sources Xcode compiles into more than one target
    cp HammerspoonOSAScriptHelper/HSOSAScriptShared.swift "Hammerspoon 2/"
    cp "Hammerspoon 2/Utilities/LoggingLevels.swift" hs2/
    cp HammerspoonIPCBroker/HSIPCShared.swift "Hammerspoon 2/"
    cp HammerspoonIPCBroker/HSIPCShared.swift hs2/

    # swift-mqtt only needs NWConnection, so it builds with the app's macOS 26 floor
    substituteInPlace Packages/swift-mqtt/Package.swift \
      --replace-fail 'platforms: [.macOS("27.0")]' 'platforms: [.macOS(.v26)]'

    substituteInPlace scripts/extract-docs.js \
      --replace-fail "new Date().toISOString()" "new Date(process.env.SOURCE_DATE_EPOCH * 1000).toISOString()"
  '';

  preBuild = ''
    npm run docs:generate
  '';

  xcodeProject = "Hammerspoon 2.xcodeproj";
  appResources = [
    "Hammerspoon 2/Assets.xcassets"
    "Hammerspoon 2/AppIcon.icon"
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
      "swiftpmVendor"
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
