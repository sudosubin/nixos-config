{
  fetchurl,
  lib,
  stdenvNoCC,
  _7zz,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "redisinsight";
  version = "3.6.0";

  src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

  sourceRoot =
    let
      arch = if stdenvNoCC.hostPlatform.system == "aarch64-darwin" then "arm64" else "x64";
    in
    "Redis Insight ${finalAttrs.version}-${arch}/Redis Insight.app";

  nativeBuildInputs = [ _7zz ];

  installPhase = ''
    mkdir -p "$out/Applications/Redis Insight.app"
    cp -R . "$out/Applications/Redis Insight.app"
  '';

  passthru = {
    sources = {
      aarch64-darwin = fetchurl {
        url = "https://s3.amazonaws.com/redisinsight.download/public/releases/${finalAttrs.version}/Redis-Insight-mac-arm64.dmg";
        hash = "sha256-SV7/wOvfyagcO99JqPs+09G2wh6Wt5B3CT6RvpQSzz8=";
      };
      x86_64-darwin = fetchurl {
        url = "https://s3.amazonaws.com/redisinsight.download/public/releases/${finalAttrs.version}/Redis-Insight-mac-x64.dmg";
        hash = "sha256-lKukd3ljXax2JJLg9B6BeKzJ9mr/Ynx+d0RtPM2sIDk=";
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
