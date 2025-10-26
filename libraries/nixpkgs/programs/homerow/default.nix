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
  version = "1.4.1";

  src = fetchurl {
    url = "https://builds.homerow.app/v${finalAttrs.version}/Homerow.zip";
    sha256 = "01m0ilcgdw7i3l2kjaviaz1x16k57zvqpay2ai2x5snpz1xh4ssl";
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
