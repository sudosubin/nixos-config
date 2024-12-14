{ lib, stdenvNoCC, fetchurl, curl, jq, runCommand, unzip }:

stdenvNoCC.mkDerivation rec {
  pname = "homerow";
  version = "1.3.2";

  src = fetchurl {
    url = "https://builds.homerow.app/v${version}/Homerow.zip";
    name = "Homerow.app";
    sha256 = "0ckksjfmfn24g5bsg1ws6a8lhnfxp74m5skg0gwzkhz7jh17bh9i";
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
