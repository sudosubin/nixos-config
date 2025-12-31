{
  lib,
  fetchzip,
  stdenvNoCC,
  nix-update-script,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "deskpad";
  version = "1.3.2";

  src = fetchzip {
    url = "https://github.com/Stengo/DeskPad/releases/download/v${finalAttrs.version}/DeskPad.app.zip";
    hash = "sha256-MY7N7Bw35Ox/y+EX/reSkMeui+PxoR+Djb7trDcbEnc=";
  };

  installPhase = ''
    mkdir -p "$out/Applications/DeskPad.app"
    cp -R . "$out/Applications/DeskPad.app"
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "A virtual monitor for screen sharing";
    homepage = "https://github.com/Stengo/DeskPad";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.darwin;
  };
})
