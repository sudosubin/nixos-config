{ lib, stdenvNoCC, fetchurl, curl, jq, runCommand, unzip }:

stdenvNoCC.mkDerivation rec {
  pname = "homerow";
  version = "1.4.0";

  src = fetchurl {
    url = "https://builds.homerow.app/v${version}/Homerow.zip";
    name = "Homerow.app";
    sha256 = "1cb1qc4kwb3w5x7s6ag0q4mygawcngmvy29viyn6sk3n28jng3wd";
  };

  nativeBuildInputs = [ unzip ];

  unpackPhase = ''
    unzip $src
  '';

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
