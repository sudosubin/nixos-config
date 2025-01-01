{ lib, fetchurl, stdenvNoCC, _7zz }:

let
  sources = {
    "aarch64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/Redis-Insight-mac-arm64.dmg";
      sha256 = "0jsrikayq77b6f9fjcdf56pa3r07inzcf13bc6lay5lclhdz2s0a";
    };
    "x86_64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/Redis-Insight-mac-x64.dmg";
      sha256 = "0p48yh6wjlirqbg6k8y10vgfp0dbi6jg27m91nqvilk1ch33n7ss";
    };
  };

in
stdenvNoCC.mkDerivation rec {
  pname = "redisinsight";
  version = "2.64.1";

  src = fetchurl {
    inherit (sources.${stdenvNoCC.hostPlatform.system}) url sha256;
  };

  sourceRoot = "Redis Insight.app";

  nativeBuildInputs = [ _7zz ];

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
