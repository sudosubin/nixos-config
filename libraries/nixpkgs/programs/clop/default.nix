final: { lib, fetchurl, stdenvNoCC, undmg, ... }@prev:

let
  hdiutil = "/usr/bin/hdiutil";

in
{
  clop = stdenvNoCC.mkDerivation rec {
    pname = "clop";
    version = "2.2.3";

    src = fetchurl {
      url = "https://github.com/FuzzyIdeas/Clop/releases/download/v${version}/Clop-${version}.dmg";
      sha256 = "171lszpx45kb0hcxpy2hxyfk58zf5fpfwqd1173adfy6jl8mg6yx";
    };

    sourceRoot = "Clop.app";

    unpackPhase = ''
      mkdir -p ./Applications
      ${hdiutil} attach -readonly -mountpoint mnt $src
      cp -r "mnt/${sourceRoot}" .
      ${hdiutil} detach -force mnt
    '';

    installPhase = ''
      mkdir -p "$out/Applications/${sourceRoot}"
      cp -R . "$out/Applications/${sourceRoot}"
    '';

    meta = with lib; {
      homepage = "https://lowtechguys.com/clop/";
      description = "Clipboard optimizer for macOS";
      license = licenses.gpl3;
      platforms = platforms.darwin;
      maintainers = [ maintainers.sudosubin ];
    };
  };
}
