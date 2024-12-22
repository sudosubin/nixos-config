{ lib, fetchurl, stdenvNoCC, _7zz }:

let
  sources = {
    "aarch64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/Redis-Insight-mac-arm64.dmg";
      sha256 = "1pwdw8s0yybpm3kz1dcjmwvvns0aph6bbnzcmwbdbvf2z9rr7g76";
    };
    "x86_64-darwin" = {
      url = "https://download.redisinsight.redis.com/latest/Redis-Insight-mac-x64.dmg";
      sha256 = "0y0l4hjm1hhya2333mza2s7sfvrh7lcm2g3sk2nsmghikz1sp95x";
    };
  };

in
stdenvNoCC.mkDerivation rec {
  pname = "redisinsight";
  version = "2.64.0";

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
