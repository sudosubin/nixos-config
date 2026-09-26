{
  fetchurl,
  lib,
  stdenvNoCC,
  _7zz,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "atlas";
  version = "0.3.3";

  src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

  sourceRoot = "Atlas/Atlas.app";

  nativeBuildInputs = [ _7zz ];

  installPhase = ''
    runHook preInstall

    mkdir -p "$out/Applications/Atlas.app"
    cp -R . "$out/Applications/Atlas.app"

    runHook postInstall
  '';

  passthru = {
    sources = {
      aarch64-darwin = fetchurl {
        url = "https://github.com/pacifio/atlas/releases/download/alpha-${finalAttrs.version}/Atlas_${finalAttrs.version}_aarch64.dmg";
        hash = "sha256-JGDjy9xc7+QnImfUFg0PoerJUmA2SJTSwDnm2AUjIws=";
      };
    };
    updateScript = ./update.sh;
  };

  meta = {
    description = "Desktop client for Agent Client Protocol coding agents";
    homepage = "https://github.com/pacifio/atlas";
    license = lib.licenses.asl20;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = builtins.attrNames finalAttrs.passthru.sources;
  };
})
