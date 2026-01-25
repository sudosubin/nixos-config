{
  lib,
  stdenvNoCC,
  fetchurl,
  undmg,
  makeWrapper,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "ungoogled-chromium";
  version = "144.0.7559.59";

  src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

  sourceRoot = "Chromium.app";

  nativeBuildInputs = [
    undmg
    makeWrapper
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
        url = "https://github.com/ungoogled-software/ungoogled-chromium-macos/releases/download/144.0.7559.59-1.1/ungoogled-chromium_144.0.7559.59-1.1_x86_64-macos.dmg";
        hash = "sha256-ZFcEP5HGVqfMnzojljCapJXbAGHubHfv7XLQVSfjDjw=";
      };
      aarch64-darwin = fetchurl {
        url = "https://github.com/ungoogled-software/ungoogled-chromium-macos/releases/download/144.0.7559.59-1.1/ungoogled-chromium_144.0.7559.59-1.1_arm64-macos.dmg";
        hash = "sha256-a2rPrOpR+25FbzP4MfG9CFA13zyRhfGpNLN2WJkb7+A=";
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
