{ lib, fetchurl, stdenvNoCC }:

let
  hdiutil = "/usr/bin/hdiutil";

in
stdenvNoCC.mkDerivation rec {
  pname = "clop";
  version = "2.5.4";

  src = fetchurl {
    url = "https://github.com/FuzzyIdeas/Clop/releases/download/v${version}/Clop-${version}.dmg";
    sha256 = "0na3556n8wkiv5f12ffi0f9r1m6qlj3gqv24c1gxrlzcc1200ina";
  };

  sourceRoot = "Clop.app";

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
    homepage = "https://lowtechguys.com/clop/";
    description = "Clipboard optimizer for macOS";
    license = licenses.gpl3;
    platforms = platforms.darwin;
    maintainers = [ maintainers.sudosubin ];
  };
}
