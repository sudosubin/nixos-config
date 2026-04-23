{
  fetchurl,
  lib,
  stdenvNoCC,
  unzip,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "figma-agent";
  version = "126.1.2";

  src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

  nativeBuildInputs = [ unzip ];

  installPhase = ''
    runHook preInstall

    mkdir -p "$out/Applications" "$out/bin"
    cp -R FigmaAgent.app "$out/Applications/"
    ln -s "$out/Applications/FigmaAgent.app/Contents/MacOS/figma_agent" "$out/bin/figma-agent"

    runHook postInstall
  '';

  passthru = {
    sources = {
      aarch64-darwin = fetchurl {
        url = "https://desktop.figma.com/agent/mac-arm/FigmaAgent-${finalAttrs.version}.zip";
        hash = "sha256-GHeiXX1/juTtotuNJH0BAV+kzIlgPxanx2/3FUjIdhE=";
      };
      x86_64-darwin = fetchurl {
        url = "https://desktop.figma.com/agent/mac/FigmaAgent-${finalAttrs.version}.zip";
        hash = "sha256-mbo3UF7tlbsaYI3O7yrpT/8x/bMBH9tthFcj3DQA/ZE=";
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
