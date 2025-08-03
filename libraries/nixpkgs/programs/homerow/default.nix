{
  lib,
  stdenvNoCC,
  fetchurl,
  curl,
  jq,
  runCommand,
  unzip,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "homerow";
  version = "1.4.0";

  src = fetchurl {
    url = "https://builds.homerow.app/v${finalAttrs.version}/Homerow.zip";
    sha256 = "1cb1qc4kwb3w5x7s6ag0q4mygawcngmvy29viyn6sk3n28jng3wd";
  };

  nativeBuildInputs = [ unzip ];

  sourceRoot = "Homerow.app";

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/Applications/${finalAttrs.sourceRoot}"
    cp -R . "$out/Applications/${finalAttrs.sourceRoot}"
    runHook postInstall
  '';

  meta = {
    description = "Keyboard shortcuts for every button in macOS";
    homepage = "https://homerow.app";
    license = lib.licenses.unfree;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.darwin;
  };
})
