{
  lib,
  fetchurl,
  stdenvNoCC,
  _7zz,
  nix-update-script,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "clop";
  version = "2.10.7";

  src = fetchurl {
    url = "https://github.com/FuzzyIdeas/Clop/releases/download/v${finalAttrs.version}/Clop-${finalAttrs.version}.dmg";
    hash = "sha256-K41JohlrvVK159DBAvF+07BGW1SyiRzYz/l7tEoRQWk=";
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
