{
  lib,
  fetchurl,
  stdenvNoCC,
  _7zz,
}:

let
  inherit (stdenvNoCC) hostPlatform;
  version = "3.0.0";
  sources = {
    aarch64-darwin = fetchurl {
      url = "https://s3.amazonaws.com/redisinsight.download/public/releases/${version}/Redis-Insight-mac-arm64.dmg";
      sha256 = "1ygabd48w2jnkbvsmymy6cljvp76d6pmpj0zsjv4k92yawvghf2q";
    };
    x86_64-darwin = fetchurl {
      url = "https://s3.amazonaws.com/redisinsight.download/public/releases/${version}/Redis-Insight-mac-x64.dmg";
      sha256 = "12xpbddkp6jlxzijszkg2rcdq3q99zrfy3qxhzw5kjwcslfnw821";
    };
  };

in
stdenvNoCC.mkDerivation (finalAttrs: {
  inherit version;
  pname = "redisinsight";

  src = sources.${hostPlatform.system};

  sourceRoot = "Redis Insight.app";

  nativeBuildInputs = [ _7zz ];

  installPhase = ''
    mkdir -p "$out/Applications/${finalAttrs.sourceRoot}"
    cp -R . "$out/Applications/${finalAttrs.sourceRoot}"
  '';

  meta = {
    description = "GUI for streamlined Redis application development";
    homepage = "https://redis.com/redis-enterprise/redis-insight/";
    license = lib.licenses.unfree;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = builtins.attrNames sources;
  };
})
