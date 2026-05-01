{
  fetchurl,
  lib,
  stdenvNoCC,
  unzip,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "figma-agent";
  version = "126.3.12";

  src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

  nativeBuildInputs = [ unzip ];

  installPhase = ''
    runHook preInstall

    mkdir -p "$out/Applications" "$out/bin"
    cp -R . "$out/Applications/FigmaAgent.app"
    ln -s "$out/Applications/FigmaAgent.app/Contents/MacOS/figma_agent" "$out/bin/figma-agent"

    runHook postInstall
  '';

  passthru = {
    sources = {
      aarch64-darwin = fetchurl {
        url = "https://desktop.figma.com/agent/mac-arm/FigmaAgent-${finalAttrs.version}.zip";
        hash = "sha256-4lzCdX31wJWOwYWtIKMFUhNX41R5+ocUC1aULKNYklY=";
      };
      x86_64-darwin = fetchurl {
        url = "https://desktop.figma.com/agent/mac/FigmaAgent-${finalAttrs.version}.zip";
        hash = "sha256-Vh0oyN8dLVljRWa3W5RixzR2ssFx/u5iHZWYjhi1djk=";
      };
    };
    updateScript = ./update.sh;
  };

  meta = {
    mainProgram = "figma-agent";
    description = "Local Figma agent server";
    homepage = "https://www.figma.com/";
    license = lib.licenses.unfree;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = builtins.attrNames finalAttrs.passthru.sources;
  };
})
