{
  apple-sdk_14,
  fetchFromGitHub,
  lib,
  stdenv,
  swift,
}:

stdenv.mkDerivation (finalAttrs: {
  pname = "wifi-unredactor";
  version = "2.0-unstable-2025-12-17";

  src = fetchFromGitHub {
    owner = "noperator";
    repo = "wifi-unredactor";
    rev = "5f7acf66c007fa65f0b3f9e6f81bff5d392b34dd";
    hash = "sha256-N4nLVIwlMoDX12UoM4jmqqZ4Zf09HDO5LmDeiRGhNpM=";
  };

  nativeBuildInputs = [ swift ];
  buildInputs = [ apple-sdk_14 ];

  buildPhase = ''
    runHook preBuild
    swiftc -o wifi-unredactor \
      "WiFi Unredactor.app/Contents/MacOS/wifi-unredactor.swift" \
      -framework Cocoa -framework CoreLocation -framework CoreWLAN
    runHook postBuild
  '';

  # Ships only the .app (exclude bin)
  installPhase = ''
    runHook preInstall

    appDir="$out/Applications/WiFi Unredactor.app"
    mkdir -p "$appDir/Contents/MacOS"
    cp "WiFi Unredactor.app/Contents/Info.plist" "$appDir/Contents/Info.plist"
    cp wifi-unredactor "$appDir/Contents/MacOS/wifi-unredactor"

    runHook postInstall
  '';

  meta = {
    description = "Bypass Wi-Fi (B)SSID redaction on CLI in macOS Sonoma+";
    homepage = "https://github.com/noperator/wifi-unredactor";
    license = lib.licenses.unlicense;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.darwin;
  };
})
