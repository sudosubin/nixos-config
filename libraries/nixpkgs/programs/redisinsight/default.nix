{ lib, fetchurl, stdenvNoCC, undmg }:

let
  sources = {
    "aarch64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/RedisInsight-mac-arm64.dmg";
      sha256 = "10y52nlbiqs7f85r1d83z4y68mbgzs5z7zaiq01spjbxfpdanpch";
    };
    "x86_64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/RedisInsight-mac-x64.dmg";
      sha256 = "06r668l4bjx2s3p19n7av8717y05lq90dzss42mnlm7y684zjhxi";
    };
  };

in
stdenvNoCC.mkDerivation rec {
  pname = "redisinsight";
  version = "2.48.0";

  src = fetchurl {
    inherit (sources.${stdenvNoCC.hostPlatform.system}) url sha256;
  };

  sourceRoot = "Redis Insight.app";

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
