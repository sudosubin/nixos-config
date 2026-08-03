{
  fetchurl,
  lib,
  stdenvNoCC,
  _7zz,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "redisinsight";
  version = "3.8.0";

  src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

  sourceRoot = "Redis Insight ${finalAttrs.version}-arm64/Redis Insight.app";

  nativeBuildInputs = [ _7zz ];

  installPhase = ''
    mkdir -p "$out/Applications/Redis Insight.app"
    cp -R . "$out/Applications/Redis Insight.app"
  '';

  passthru = {
    sources = {
      aarch64-darwin = fetchurl {
        url = "https://s3.amazonaws.com/redisinsight.download/public/releases/${finalAttrs.version}/Redis-Insight-mac-arm64.dmg";
        hash = "sha256-r1jCGLCbKj0Qum8paWn815KmVE/w29iYRYBOq4bwXds=";
      };
    };
    updateScript = ./update.sh;
  };

  meta = {
    description = "GUI for streamlined Redis application development";
    homepage = "https://redis.com/redis-enterprise/redis-insight/";
    license = lib.licenses.unfree;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = builtins.attrNames finalAttrs.passthru.sources;
  };
})
