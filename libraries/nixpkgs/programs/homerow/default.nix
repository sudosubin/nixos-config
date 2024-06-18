{ lib, stdenvNoCC, fetchzip, curl, jq, runCommand }:

stdenvNoCC.mkDerivation rec {
  pname = "homerow";
  version = "1.0.0";

  src = fetchzip {
    url = "https://builds.homerow.app/latest/Homerow.zip";
    name = "Homerow.app";
    sha256 = "09w6jljrscxrvnwnfq9ywsdnqv08iy7fw1p0v1ygkyd8dai2jx1w";
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
