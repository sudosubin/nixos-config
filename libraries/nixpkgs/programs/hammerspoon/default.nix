{
  lib,
  fetchurl,
  stdenvNoCC,
  unzip,
}:

stdenvNoCC.mkDerivation rec {
  pname = "hammerspoon";
  version = "1.0.0";

  src = fetchurl {
    url = "https://github.com/Hammerspoon/hammerspoon/releases/download/${version}/Hammerspoon-${version}.zip";
    sha256 = "0zkagvnzf2ia68l998nzblqvvgl5xy8qv57mx03c6zd4bnsh5dsx";
  };

  sourceRoot = "Hammerspoon.app";

  nativeBuildInputs = [ unzip ];

  unpackPhase = ''
    unzip $src
  '';

  installPhase = ''
    mkdir -p "$out/Applications/${sourceRoot}"
    cp -R . "$out/Applications/${sourceRoot}"
  '';

  meta = with lib; {
    homepage = "http://www.hammerspoon.org/";
    description = "Staggeringly powerful macOS desktop automation with Lua";
    license = licenses.mit;
    platforms = platforms.darwin;
    maintainers = [ maintainers.sudosubin ];
  };
}
