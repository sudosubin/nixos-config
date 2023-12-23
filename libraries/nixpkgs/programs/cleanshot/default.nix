{ lib, fetchurl, stdenvNoCC }:

let
  hdiutil = "/usr/bin/hdiutil";

in
stdenvNoCC.mkDerivation rec {
  pname = "cleanshot";
  version = "4.6.2";

  src = fetchurl {
    url = "https://updates.getcleanshot.com/v3/CleanShot-X-${version}.dmg";
    sha256 = "04qf45v7x54729i5zpbq1f60811db6jvy15rax6184zpsdd13fxv";
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
}
