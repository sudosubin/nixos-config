final: { lib, stdenvNoCC, fetchurl, undmg, ... }@prev:

let
  ver = "5.0.5";
  build = "2096";

in
{
  alfred5 = stdenvNoCC.mkDerivation rec {
    pname = "alfred";
    version = "${ver}.${build}";

    src = fetchurl {
      url = "https://cachefly.alfredapp.com/Alfred_${ver}_${build}.dmg";
      name = "Alfred_${ver}_${build}.dmg";
      sha256 = "sha256-nSh0XOCp4SorzRMoFlehtPi0kqY+TqKxhhomG2JqOK0=";
    };

    sourceRoot = "Alfred 5.app";

    nativeBuildInputs = [ undmg ];

    installPhase = ''
      mkdir -p "$out/Applications/Alfred 5.app"
      cp -R . "$out/Applications/Alfred 5.app"
    '';

    meta = with lib;  {
      homepage = "https://www.alfredapp.com/";
      description = "Application launcher and productivity software";
      license = licenses.unfree;
      platforms = platforms.darwin;
      maintainers = [ maintainers.sudosubin ];
    };
  };
}
