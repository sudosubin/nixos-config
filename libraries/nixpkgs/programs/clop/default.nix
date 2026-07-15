{
  fetchurl,
  lib,
  nix-update-script,
  stdenvNoCC,
  _7zz,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "clop";
  version = "3.3.0";

  src = fetchurl {
    url = "https://github.com/FuzzyIdeas/Clop/releases/download/v${finalAttrs.version}/Clop-${finalAttrs.version}.dmg";
    hash = "sha256-n0H7VJm905V7s/XhizaqBbMcLtOPOJD89laBxyKob0k=";
  };

  sourceRoot = "Clop.app";

  nativeBuildInputs = [ _7zz ];

  installPhase = ''
    mkdir -p "$out/Applications/${finalAttrs.sourceRoot}"
    cp -R . "$out/Applications/${finalAttrs.sourceRoot}"
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Clipboard optimizer for macOS";
    homepage = "https://lowtechguys.com/clop/";
    license = lib.licenses.gpl3;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.darwin;
  };
})
