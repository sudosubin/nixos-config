final: { lib, fetchurl, stdenvNoCC, undmg, ... }@prev:

let
  sources = {
    "aarch64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/RedisInsight-v2-mac-arm64.dmg";
      sha256 = "0mr2s3dz11h67dx295dvvni3zmnfkq7i67iqwdcmb0rs5jl1883b";
    };
    "x86_64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/RedisInsight-v2-mac-x64.dmg";
      sha256 = "1xf267gqfja7578ggh0cq7bffdhxz8zc6zdrcnmf7s5jfdrqsl1a";
    };
  };

in
{
  redisinsight = stdenvNoCC.mkDerivation rec {
    pname = "redisinsight";
    version = "2.38.0";

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
