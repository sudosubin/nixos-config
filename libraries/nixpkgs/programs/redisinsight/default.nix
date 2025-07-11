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
      sha256 = "0wdmr1xfglxkjvci4fsfmmazkgq5bbvjjn6lqwgd7a24d4ax93ir";
    };
    "x86_64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/Redis-Insight-mac-x64.dmg";
      sha256 = "10bpwbf64nbmiv5rsn2jmi4cd1r1dq310lq5aans4sgfiifqnb1c";
    };
  };

in
stdenvNoCC.mkDerivation rec {
  pname = "redisinsight";
  version = "2.70.1";

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
