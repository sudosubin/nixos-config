final: { lib, fetchurl, stdenvNoCC, undmg, ... }@prev:

let
  hdiutil = "/usr/bin/hdiutil";

in
{
  clop = stdenvNoCC.mkDerivation rec {
    pname = "clop";
    version = "2.2.6";

    src = fetchurl {
      url = "https://github.com/FuzzyIdeas/Clop/releases/download/v${version}/Clop-${version}.dmg";
      sha256 = "0hs7y7r8yl76nc0rw0v9h5q5bg52509fj80jiibg02a5xwyx2gzy";
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
