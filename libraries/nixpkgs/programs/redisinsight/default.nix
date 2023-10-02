final: { lib, fetchurl, stdenvNoCC, undmg, ... }@prev:

let
  sources = {
    "aarch64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/RedisInsight-v2-mac-arm64.dmg";
      sha256 = "1h0a3qy9p0slnrlglba7kmrz6w7f9gkhvgqdwg5a61hh8facp5fj";
    };
    "x86_64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/RedisInsight-v2-mac-x64.dmg";
      sha256 = "144maf5cy8yviy50rq9399dkylk1npysqvh57g4a59qyj49dfqg5";
    };
  };

in
{
  redisinsight = stdenvNoCC.mkDerivation rec {
    pname = "redisinsight";
    version = "2.34.0";

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
