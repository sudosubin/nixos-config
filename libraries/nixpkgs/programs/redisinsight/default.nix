final: { lib, fetchurl, stdenvNoCC, undmg, ... }@prev:

let
  sources = {
    "aarch64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/RedisInsight-v2-mac-arm64.dmg";
      sha256 = "1vh94y113clnrrgcfj0lgblfx0y86rfq8x8rnjs5n58aq949m95v";
    };
    "x86_64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/RedisInsight-v2-mac-x64.dmg";
      sha256 = "0d5mjk7qzk6yijfwkgs1w5kvp6asggnjajf33fa0jkhsv6ncdrvy";
    };
  };

in
{
  redisinsight = stdenvNoCC.mkDerivation rec {
    pname = "redisinsight";
    version = "2.32";

    src = fetchurl {
      inherit (sources.${stdenvNoCC.hostPlatform.system}) url sha256;
    };

    sourceRoot = "RedisInsight-v2.app";

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
  };
}
