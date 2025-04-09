{
  lib,
  stdenvNoCC,
  fetchzip,
}:

stdenvNoCC.mkDerivation rec {
  pname = "apple-cursor-theme";
  version = "1.2.3";

  src = fetchzip {
    url = "https://github.com/ful1e5/apple_cursor/releases/download/v${version}/macOSBigSur.tar.gz";
    sha256 = "sha256-EvIoUq5g6+NynSPEylTj8tDUFEitGjxDw7CrhEgOlV8=";
  };

  installPhase = ''
    mkdir -p $out/share/icons/apple-cursor-theme
    cp -r . $out/share/icons/apple-cursor-theme
  '';

  meta = {
    description = "Free & Open source macOS Cursors";
    homepage = "https://github.com/ful1e5/apple_cursor";
    license = lib.licenses.gpl3;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.linux;
  };
}
