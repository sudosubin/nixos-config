{
  lib,
  fetchurl,
  stdenvNoCC,
  _7zz,
}:

let
  inherit (stdenvNoCC) hostPlatform;
  sources = {
    aarch64-darwin = fetchurl {
      url = "https://download.redisinsight.redis.com/latest/Redis-Insight-mac-arm64.dmg";
      sha256 = "0d6bkwgnxyvvlx4lzs783v8crbxrmy98kdsa1l2jbiswbf24gy1f";
    };
    x86_64-darwin = fetchurl {
      url = "https://download.redisinsight.redis.com/latest/Redis-Insight-mac-x64.dmg";
      sha256 = "1fnhbmlj0d1r3fhq9smq1ygwqzv4hiqd5xndcsxaxkw1mvifsgf3";
    };
  };

in
stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "redisinsight";
  version = "3.0.0";

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
