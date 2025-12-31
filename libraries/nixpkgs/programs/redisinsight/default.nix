{
  lib,
  fetchurl,
  stdenvNoCC,
  _7zz,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "redisinsight";
  version = "3.0.0";

  src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

  sourceRoot = "Redis Insight.app";

  nativeBuildInputs = [ _7zz ];

  installPhase = ''
    mkdir -p "$out/Applications/${finalAttrs.sourceRoot}"
    cp -R . "$out/Applications/${finalAttrs.sourceRoot}"
  '';

  passthru = {
    sources = {
      aarch64-darwin = fetchurl {
        url = "https://s3.amazonaws.com/redisinsight.download/public/releases/${finalAttrs.version}/Redis-Insight-mac-arm64.dmg";
        hash = "sha256-WDj4NldepEm21B/IW69p5twtKTO++qr3mlYKjkhb6vk=";
      };
      x86_64-darwin = fetchurl {
        url = "https://s3.amazonaws.com/redisinsight.download/public/releases/${finalAttrs.version}/Redis-Insight-mac-x64.dmg";
        hash = "sha256-QSBuHdWMy1n4hx0P7/JPCQ/cWBZvfi3j71SaO1tbt4s=";
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
