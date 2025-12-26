{
  lib,
  fetchurl,
  stdenvNoCC,
  unzip,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "hammerspoon";
  version = "1.1.0";

  src = fetchurl {
    url = "https://github.com/Hammerspoon/hammerspoon/releases/download/${finalAttrs.version}/Hammerspoon-${finalAttrs.version}.zip";
    sha256 = "1dbk3vacrbfpylgnm94ankk8pb5bf8vywnwdfwwcvxl4g5xr1vrr";
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
