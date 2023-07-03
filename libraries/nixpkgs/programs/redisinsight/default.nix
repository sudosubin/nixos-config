final: { lib, fetchurl, stdenvNoCC, undmg, ... }@prev:

let
  sources = {
    "aarch64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/RedisInsight-v2-mac-arm64.dmg";
      sha256 = "1d1169lm9kyg6zlgfbmjavgi9ba4n15d0ygmjlbavrl7p5qixk15";
    };
    "x86_64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/RedisInsight-v2-mac-x64.dmg";
      sha256 = "0d7gphf9nsl7grvhxf6xwiqdxwrv4rz6210s8g4wh1crddwcg39c";
    };
  };

in
{
  redisinsight = stdenvNoCC.mkDerivation rec {
    pname = "redisinsight";
    version = "2.28.0";

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
