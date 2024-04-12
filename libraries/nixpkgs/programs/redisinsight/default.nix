{ lib, fetchurl, stdenvNoCC, undmg }:

let
  sources = {
    "aarch64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/RedisInsight-mac-arm64.dmg";
      sha256 = "0n5g433q336srmh0q13kbbscfb3vf1im4fywbq7szqqblsx6cdca";
    };
    "x86_64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/RedisInsight-mac-x64.dmg";
      sha256 = "08q6p35lb91hcph58a2qfg8cl9n3rf4yvlx6w7j6hq979ybd8a43";
    };
  };

in
stdenvNoCC.mkDerivation rec {
  pname = "redisinsight";
  version = "2.46.0";

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
