{
  fetchzip,
  lib,
  nix-update-script,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "hammerspoon";
  version = "1.1.0";

  src = fetchzip {
    url = "https://github.com/Hammerspoon/hammerspoon/releases/download/${finalAttrs.version}/Hammerspoon-${finalAttrs.version}.zip";
    hash = "sha256-rfgG1xQk+uSrRPiOgMpJ9F6unmlhg6cfrTCHCal1NlE=";
  };

  installPhase = ''
    mkdir -p "$out/Applications/Hammerspoon.app"
    cp -R . "$out/Applications/Hammerspoon.app"
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Staggeringly powerful macOS desktop automation with Lua";
    homepage = "http://www.hammerspoon.org/";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.darwin;
  };
})
