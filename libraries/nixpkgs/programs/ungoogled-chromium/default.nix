{
  fetchurl,
  lib,
  stdenvNoCC,
  undmg,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "ungoogled-chromium";
  version = "145.0.7632.159";

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
        url = "https://github.com/ungoogled-software/ungoogled-chromium-macos/releases/download/145.0.7632.159-1.1/ungoogled-chromium_145.0.7632.159-1.1_x86_64-macos.dmg";
        hash = "sha256-UYGRAV4EDuO3WM1gUU/fcSROl4Y9t3xZWUdmGs1ThRY=";
      };
      aarch64-darwin = fetchurl {
        url = "https://github.com/ungoogled-software/ungoogled-chromium-macos/releases/download/145.0.7632.159-1.1/ungoogled-chromium_145.0.7632.159-1.1_arm64-macos.dmg";
        hash = "sha256-c3/V9t8HXMCVQrRMMPblIhiBs+lubUKHlPG5pmQSjvk=";
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
