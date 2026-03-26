{
  fetchurl,
  lib,
  stdenvNoCC,
  undmg,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "ungoogled-chromium";
  version = "146.0.7680.153";

  src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

  sourceRoot = "Chromium.app";

  nativeBuildInputs = [
    undmg
  ];

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/Applications"
    cp -r . "$out/Applications/$sourceRoot"
    runHook postInstall
  '';

  passthru = {
    sources = {
      x86_64-darwin = fetchurl {
        url = "https://github.com/ungoogled-software/ungoogled-chromium-macos/releases/download/146.0.7680.153-1.1/ungoogled-chromium_146.0.7680.153-1.1_x86_64-macos.dmg";
        hash = "sha256-9Vm7hcBr8YFwUOW8DSgoc9gMK5YxB0VjT0fbP5FzYC0=";
      };
      aarch64-darwin = fetchurl {
        url = "https://github.com/ungoogled-software/ungoogled-chromium-macos/releases/download/146.0.7680.153-1.1/ungoogled-chromium_146.0.7680.153-1.1_arm64-macos.dmg";
        hash = "sha256-NBM4PkMQjcgFOyKdy8+V4quJGg5wZdmIKHGSj3USHnI=";
      };
    };
    updateScript = ./update.sh;
  };

  meta = {
    description = "Open source web browser from Google, with dependencies on Google web services removed (binary release)";
    homepage = "https://github.com/ungoogled-software/ungoogled-chromium-macos";
    license = lib.licenses.bsd3;
    sourceProvenance = with lib.sourceTypes; [ binaryNativeCode ];
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = builtins.attrNames finalAttrs.passthru.sources;
  };
})
