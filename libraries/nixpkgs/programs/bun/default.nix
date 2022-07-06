final: { lib, fetchzip, stdenv, freetype, ... }@prev:

let
  inherit (stdenv.hostPlatform) system;

  version = "0.1.1";

  url = {
    x86_64-linux = "https://github.com/Jarred-Sumner/bun/releases/download/bun-v${version}/bun-linux-x64.zip";
    x86_64-darwin = "https://github.com/Jarred-Sumner/bun/releases/download/bun-v${version}/bun-darwin-x64.zip";
    aarch64-darwin = "https://github.com/Jarred-Sumner/bun/releases/download/bun-v${version}/bun-darwin-aarch64.zip";
  }.${system};

  sha256 = {
    x86_64-linux = "1v45ivqlnaik61dic8d42s4whjz409ywa2jgh1yq5bndsx63knvl";
    x86_64-darwin = "0kslc1bpjnrjkamd4mh59bmwzbs7vr98xhs1v7gbgw13zs50496a";
    aarch64-darwin = "0z10i6p9fvmccz5flllga07yfakd1776q0k17amplf8xzpzy9bzz";
  }.${system};

in
{
  bun = stdenv.mkDerivation rec {
    inherit version;
    pname = "bun";

    src = fetchzip {
      inherit url sha256;
    };

    installPhase = ''
      install -d $out/bin
      install -m755 bun $out/bin/
    '';

    meta = with lib; {
      homepage = "https://bun.sh";
      description = "Incredibly fast JavaScript runtime, bundler, transpiler and package manager - all in one";
      license = licenses.mit;
      platforms = [ "x86_64-linux" "x86_64-darwin" "aarch64-darwin" ];
      maintainers = [ maintainers.sudosubin ];
    };
  };
}
