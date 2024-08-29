{ lib, stdenvNoCC, fetchzip, curl, jq, runCommand }:

stdenvNoCC.mkDerivation rec {
  pname = "homerow";
  version = "1.2.2";

  src = fetchzip {
    url = "https://builds.homerow.app/latest/Homerow.zip";
    name = "Homerow.app";
    sha256 = "11mw54gh7h17jzknn0ngjc6r5pm0qfbgc1a1cjnxby1p5w7gs787";
  };

  sourceRoot = "Homerow.app";

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/Applications/${sourceRoot}"
    cp -R . "$out/Applications/${sourceRoot}"
    runHook postInstall
  '';

  meta = with lib; {
    homepage = "https://homerow.app";
    description = "Keyboard shortcuts for every button in macOS";
    license = licenses.unfree;
    platforms = platforms.darwin;
    maintainers = [ maintainers.sudosubin ];
  };
}
