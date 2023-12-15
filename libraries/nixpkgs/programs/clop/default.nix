final: { lib, fetchurl, stdenvNoCC, undmg, ... }@prev:

let
  hdiutil = "/usr/bin/hdiutil";

in
{
  clop = stdenvNoCC.mkDerivation rec {
    pname = "clop";
    version = "2.4.0";

    src = fetchurl {
      url = "https://github.com/FuzzyIdeas/Clop/releases/download/v${version}/Clop.dmg";
      sha256 = "0lkkpywbl4k2hkardfb3nc575n3axqz30q2llph5z3b53si3jnvg";
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
