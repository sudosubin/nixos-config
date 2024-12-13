{ lib, stdenvNoCC, fetchzip, curl, jq, runCommand }:

stdenvNoCC.mkDerivation rec {
  pname = "homerow";
  version = "1.3.2";

  src = fetchzip {
    url = "https://builds.homerow.app/latest/Homerow.zip";
    name = "Homerow.app";
    sha256 = "0rb620a4zvc7vjwvcdn10y64agvan4bjplspx8d6p27k488bw588";
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
