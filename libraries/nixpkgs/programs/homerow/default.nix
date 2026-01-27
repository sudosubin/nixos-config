{
  lib,
  stdenvNoCC,
  fetchzip,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "homerow";
  version = "1.4.1";

  src = fetchzip {
    url = "https://builds.homerow.app/v${finalAttrs.version}/Homerow.zip";
    hash = "sha256-/Zp62UOvjnj+sN8VTpGC9EZ5cLsjOe/A5ZZkJAx/5Xc=";
  };

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/Applications/Homerow.app"
    cp -R . "$out/Applications/Homerow.app"
    runHook postInstall
  '';

  passthru.updateScript = ./update.sh;

  meta = {
    description = "Keyboard shortcuts for every button in macOS";
    homepage = "https://homerow.app";
    license = lib.licenses.unfree;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.darwin;
  };
})
