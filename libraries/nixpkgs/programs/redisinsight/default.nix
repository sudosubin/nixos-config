{ lib, fetchurl, stdenvNoCC, undmg }:

let
  sources = {
    "aarch64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/RedisInsight-mac-arm64.dmg";
      sha256 = "1h512cny1028xda94ip89ffsm5dsx92bafz21s39ixmjd5x48laa";
    };
    "x86_64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/RedisInsight-mac-x64.dmg";
      sha256 = "19b9yzzfmsfclb3a1i49qlfn8jzmbqavxdhvf498a4k4b0ia97xc";
    };
  };

in
stdenvNoCC.mkDerivation rec {
  pname = "redisinsight";
  version = "2.42.0";

  src = fetchurl {
    inherit (sources.${stdenvNoCC.hostPlatform.system}) url sha256;
  };

  sourceRoot = "RedisInsight.app";

  nativeBuildInputs = [ undmg ];

  unpackPhase = ''
    undmg $src
  '';

  installPhase = ''
    mkdir -p "$out/Applications/${sourceRoot}"
    cp -R . "$out/Applications/${sourceRoot}"
  '';

  meta = with lib; {
    homepage = "https://redis.com/redis-enterprise/redis-insight/";
    description = "GUI for streamlined Redis application development";
    license = licenses.unfree;
    platforms = builtins.attrNames sources;
    maintainers = [ maintainers.sudosubin ];
  };
}
