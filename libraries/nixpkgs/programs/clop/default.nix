{ lib, fetchurl, stdenvNoCC, _7zz }:

stdenvNoCC.mkDerivation rec {
  pname = "clop";
  version = "2.9.1";

  src = fetchurl {
    url = "https://github.com/FuzzyIdeas/Clop/releases/download/v${version}/Clop-${version}.dmg";
    sha256 = "0k2dz4k0n1907y9jz5kw8prsz985bdfqvh4wvsw8b9zqngxpi5ra";
  };

  sourceRoot = "Clop.app";

  nativeBuildInputs = [ _7zz ];

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
