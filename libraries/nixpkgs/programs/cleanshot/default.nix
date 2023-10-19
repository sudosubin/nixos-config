final: { lib, fetchurl, stdenvNoCC, ... }@prev:

let
  hdiutil = "/usr/bin/hdiutil";

in
{
  cleanshot = stdenvNoCC.mkDerivation rec {
    pname = "cleanshot";
    version = "4.6.1";

    src = fetchurl {
      url = "https://updates.getcleanshot.com/v3/CleanShot-X-${version}.dmg";
      sha256 = "1424mmm58zxav31anl0rfcxbj8q7h3kdg2nwp7g4gi8z4zjg6451";
    };

    sourceRoot = "CleanShot X.app";

    unpackPhase = ''
      mkdir -p ./Applications
      ${hdiutil} attach -readonly -mountpoint mnt $src
      cp -r "mnt/${sourceRoot}" .
      ${hdiutil} detach -force mnt
    '';

    installPhase = ''
      mkdir -p "$out/Applications/${sourceRoot}"
      cp -R . "$out/Applications/${sourceRoot}"
    '';

    meta = with lib; {
      homepage = "https://cleanshot.com/";
      description = "Screen capturing tool";
      license = licenses.unfree;
      platforms = platforms.darwin;
      maintainers = [ maintainers.sudosubin ];
    };
  };
}
