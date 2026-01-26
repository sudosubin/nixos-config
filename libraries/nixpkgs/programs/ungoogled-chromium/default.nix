{
  lib,
  stdenvNoCC,
  fetchurl,
  undmg,
  makeWrapper,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "ungoogled-chromium";
  version = "144.0.7559.96";

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
        url = "https://github.com/ungoogled-software/ungoogled-chromium-macos/releases/download/144.0.7559.96-1.1/ungoogled-chromium_144.0.7559.96-1.1_x86_64-macos.dmg";
        hash = "sha256-x0N5wfZuJJJns8d6RDlmlF/91KbmRr/l5gdS6dGFFmM=";
      };
      aarch64-darwin = fetchurl {
        url = "https://github.com/ungoogled-software/ungoogled-chromium-macos/releases/download/144.0.7559.96-1.1/ungoogled-chromium_144.0.7559.96-1.1_arm64-macos.dmg";
        hash = "sha256-TMgjb/6s+NzzukNCLPjTw+4ovw5uqwSYsl5ikGlSvpo=";
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
