{
  fetchurl,
  lib,
  nix-update-script,
  stdenvNoCC,
  _7zz,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "clop";
  version = "2.11.3";

  src = fetchurl {
    url = "https://github.com/FuzzyIdeas/Clop/releases/download/v${finalAttrs.version}/Clop-${finalAttrs.version}.dmg";
    hash = "sha256-uNnhDgebZi4mjZavs4TixUeNykPkgKpaCoO4bcDMigA=";
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
