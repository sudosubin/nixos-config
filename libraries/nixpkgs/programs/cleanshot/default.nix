{
  lib,
  fetchurl,
  stdenvNoCC,
  _7zz,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "cleanshot";
  version = "4.6.2";

  src = fetchurl {
    url = "https://updates.getcleanshot.com/v3/CleanShot-X-${finalAttrs.version}.dmg";
    hash = "sha256-u7sRWtP3ExRMV7kEv6VZLQQEjAt43V9iEoeUfnYhDhM=";
  };

  sourceRoot = "CleanShot X.app";

  nativeBuildInputs = [ _7zz ];

  installPhase = ''
    mkdir -p "$out/Applications/${finalAttrs.sourceRoot}"
    cp -R . "$out/Applications/${finalAttrs.sourceRoot}"
  '';

  meta = {
    description = "Screen capturing tool";
    homepage = "https://cleanshot.com/";
    license = lib.licenses.unfree;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.darwin;
  };
})
