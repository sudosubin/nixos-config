{
  lib,
  fetchurl,
  stdenvNoCC,
  unzip,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "hammerspoon";
  version = "1.0.0";

  src = fetchurl {
    url = "https://github.com/Hammerspoon/hammerspoon/releases/download/${finalAttrs.version}/Hammerspoon-${finalAttrs.version}.zip";
    sha256 = "0zkagvnzf2ia68l998nzblqvvgl5xy8qv57mx03c6zd4bnsh5dsx";
  };

  sourceRoot = "Hammerspoon.app";

  nativeBuildInputs = [ unzip ];

  installPhase = ''
    mkdir -p "$out/Applications/${finalAttrs.sourceRoot}"
    cp -R . "$out/Applications/${finalAttrs.sourceRoot}"
  '';

  meta = {
    description = "Staggeringly powerful macOS desktop automation with Lua";
    homepage = "http://www.hammerspoon.org/";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.darwin;
  };
})
