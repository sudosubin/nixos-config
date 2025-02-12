{ lib, stdenvNoCC, fetchurl, curl, jq, runCommand, unzip }:

stdenvNoCC.mkDerivation rec {
  pname = "homerow";
  version = "1.3.3";

  src = fetchurl {
    url = "https://builds.homerow.app/v${version}/Homerow.zip";
    name = "Homerow.app";
    sha256 = "1jlpqpcik9qqflf0m5gwhskk31vc2bzfhhm3hg9jdl2drx2iq04r";
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
