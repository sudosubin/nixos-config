final: { lib, fetchurl, stdenvNoCC, undmg, ... }@prev:

{
  cleanshot = stdenvNoCC.mkDerivation rec {
    pname = "cleanshot";
    version = "4.5";

    src = fetchurl {
      url = "https://updates.getcleanshot.com/v3/CleanShot-X-${version}.dmg";
      sha256 = "1xi5bcvc4586n347zxd5f2a57q00syx8kxc43p65c9n1fjpaml7c";
    };

    sourceRoot = "CleanShot X.app";

    nativeBuildInputs = [ undmg ];

    unpackPhase = ''
      undmg $src
    '';

    installPhase = ''
      mkdir -p "$out/Applications/${sourceRoot}"
      cp -R . "$out/Applications/${sourceRoot}"
    '';

    meta = with lib; {
      homepage = "https://cleanshot.com/";
      description = "Screen capturing tool";
      license = licenses.unfree;
      platforms = platforms.darwin;
      maintainers = [ maintainers.sudosubin ];
    };
  };
}
