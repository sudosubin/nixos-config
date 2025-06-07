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
      sha256 = "0hwfikljigcwpalanrrnralmmfpg8n78q32napmm2gcxs2nsv09a";
    };
    "x86_64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/Redis-Insight-mac-x64.dmg";
      sha256 = "1dnm0wfcrvyqb1mhw7yq9bjwxrbg81w9f1r5vpc1h184kzmmgnzc";
    };
  };

in
stdenvNoCC.mkDerivation rec {
  pname = "redisinsight";
  version = "2.70.0";

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
