{
  lib,
  fetchurl,
  stdenvNoCC,
  _7zz,
}:

stdenvNoCC.mkDerivation rec {
  pname = "clop";
  version = "2.9.2";

  src = fetchurl {
    url = "https://github.com/FuzzyIdeas/Clop/releases/download/v${version}/Clop-${version}.dmg";
    sha256 = "14630gdyc8rbwgp34cp2qz6m1hik0wjzjg1yfz1jvsf8yv70nir7";
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
