{
  lib,
  fetchurl,
  stdenvNoCC,
  _7zz,
}:

stdenvNoCC.mkDerivation (
  finalAttrs:
  let
    sources = {
      "aarch64-darwin" = {
        url = "https://download.redisinsight.redis.com/latest/Redis-Insight-mac-arm64.dmg";
        sha256 = "0d6bkwgnxyvvlx4lzs783v8crbxrmy98kdsa1l2jbiswbf24gy1f";
      };
      "x86_64-darwin" = {
        url = "https://download.redisinsight.redis.com/latest/Redis-Insight-mac-x64.dmg";
        sha256 = "1fnhbmlj0d1r3fhq9smq1ygwqzv4hiqd5xndcsxaxkw1mvifsgf3";
      };
    };

  in
  {
    pname = "redisinsight";
    version = "2.70.1";

    src = fetchurl {
      inherit (sources.${stdenvNoCC.hostPlatform.system}) url sha256;
    };

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
  }
)
