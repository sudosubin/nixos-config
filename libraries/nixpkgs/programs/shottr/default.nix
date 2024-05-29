{ lib, fetchurl, stdenvNoCC }:

let
  hdiutil = "/usr/bin/hdiutil";

in
stdenvNoCC.mkDerivation rec {
  pname = "shottr";
  version = "1.7.2";

  src = fetchurl {
    url = "https://shottr.cc/dl/Shottr-${version}.dmg";
    sha256 = "0k1fz4fff62njr6niq3r5vlddbyi9729richczwj53kmhv6di8zh";
  };

  sourceRoot = "Shottr.app";

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
    homepage = "https://shottr.cc/";
    description = "Screenshot measurement and annotation tool";
    license = licenses.unfree;
    platforms = platforms.darwin;
    maintainers = [ maintainers.sudosubin ];
  };
}
