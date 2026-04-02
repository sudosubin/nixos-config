{
  fetchzip,
  lib,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "homerow";
  version = "1.5.3";

  src = fetchzip {
    url = "https://builds.homerow.app/v${finalAttrs.version}/Homerow.zip";
    hash = "sha256-zqa1QYq7UF80z0cvMZJMgTQFo3vqGdwzuLVMwgyuMME=";
    stripRoot = false;
  };

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/Applications"
    cp -R Homerow.app "$out/Applications/"
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
