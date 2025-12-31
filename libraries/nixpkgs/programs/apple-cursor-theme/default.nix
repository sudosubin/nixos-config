{
  lib,
  stdenvNoCC,
  fetchzip,
  nix-update-script,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "apple-cursor-theme";
  version = "2.0.1";

  src = fetchzip {
    url = "https://github.com/ful1e5/apple_cursor/releases/download/v${finalAttrs.version}/macOS.tar.xz";
    stripRoot = false;
    hash = "sha256-nS4g+VwM+4q/S1ODb3ySi2SBk7Ha8vF8d9XpP5cEkok=";
  };

  installPhase = ''
    mkdir -p $out/share/icons/apple-cursor-theme
    cp -r ./macOS $out/share/icons/apple-cursor-theme
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Free & Open source macOS Cursors";
    homepage = "https://github.com/ful1e5/apple_cursor";
    license = lib.licenses.gpl3;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.linux;
  };
})
