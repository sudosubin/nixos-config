{ lib, fetchurl, stdenvNoCC, _7zz }:

stdenvNoCC.mkDerivation rec {
  pname = "clop";
  version = "2.8.4";

  src = fetchurl {
    url = "https://github.com/FuzzyIdeas/Clop/releases/download/v${version}/Clop-${version}.dmg";
    sha256 = "0z3ywghhb62hv740p68qvz4yhbnz1xmifs0dfvv67p030yb6vfsx";
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
