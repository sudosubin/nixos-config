{
  lib,
  fetchurl,
  stdenvNoCC,
  _7zz,
}:

let
  sources = {
    "aarch64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/Redis-Insight-mac-arm64.dmg";
      sha256 = "0h9my835h6jmjf572bb4l9gkv7axf0j73qqdnrcm1i1k9nb0gc34";
    };
    "x86_64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/Redis-Insight-mac-x64.dmg";
      sha256 = "02f6q7gpdzy7f3gynqiz631fcls2d4qh3hi3sjx3dq8vcbsz02yw";
    };
  };

in
stdenvNoCC.mkDerivation rec {
  pname = "redisinsight";
  version = "2.68.0";

  src = fetchurl {
    inherit (sources.${stdenvNoCC.hostPlatform.system}) url sha256;
  };

  sourceRoot = "Redis Insight.app";

  nativeBuildInputs = [ _7zz ];

  installPhase = ''
    mkdir -p "$out/Applications/${sourceRoot}"
    cp -R . "$out/Applications/${sourceRoot}"
  '';

  meta = {
    description = "GUI for streamlined Redis application development";
    homepage = "https://redis.com/redis-enterprise/redis-insight/";
    license = lib.licenses.unfree;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = builtins.attrNames sources;
  };
}
