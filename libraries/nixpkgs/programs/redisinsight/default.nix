final: { lib, fetchurl, stdenvNoCC, undmg, ... }@prev:

let
  sources = {
    "aarch64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/RedisInsight-v2-mac-arm64.dmg";
      sha256 = "01hlw2q7asq9crf874vyiq25799qkw5cw0nv8w8xabfbvx0x87r6";
    };
    "x86_64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/RedisInsight-v2-mac-x64.dmg";
      sha256 = "0mh7j0qyc3ck05llv70h9k40h0d9mmdhh6zckrj6r4sc8b3jv79h";
    };
  };

in
{
  redisinsight = stdenvNoCC.mkDerivation rec {
    pname = "redisinsight";
    version = "2.24.0";

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
