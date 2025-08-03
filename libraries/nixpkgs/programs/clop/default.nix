{
  lib,
  fetchurl,
  stdenvNoCC,
  _7zz,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "clop";
  version = "2.10.1";

  src = fetchurl {
    url = "https://github.com/FuzzyIdeas/Clop/releases/download/v${finalAttrs.version}/Clop-${finalAttrs.version}.dmg";
    sha256 = "182mxh278xfy62f5gfm3v67abyjid6zdnshbcfpx6455g4a9ngyd";
  };

  sourceRoot = "Clop.app";

  nativeBuildInputs = [ _7zz ];

  installPhase = ''
    mkdir -p "$out/Applications/${finalAttrs.sourceRoot}"
    cp -R . "$out/Applications/${finalAttrs.sourceRoot}"
  '';

  meta = {
    description = "Clipboard optimizer for macOS";
    homepage = "https://lowtechguys.com/clop/";
    license = lib.licenses.gpl3;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.darwin;
  };
})
