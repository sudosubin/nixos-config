{ lib, fetchurl, stdenvNoCC, _7zz }:

stdenvNoCC.mkDerivation rec {
  pname = "clop";
  version = "2.8.2";

  src = fetchurl {
    url = "https://github.com/FuzzyIdeas/Clop/releases/download/v${version}/Clop-${version}.dmg";
    sha256 = "07jxbkdhcq4hjspnhxyn9cmv9l0gmj3pgs6xc73csmxg3m6v17ka";
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
