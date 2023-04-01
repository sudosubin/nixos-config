final: { lib, fetchurl, stdenvNoCC, unzip, ... }@prev:

{
  homerow = stdenvNoCC.mkDerivation rec {
    pname = "homerow";
    version = "0.18";

    src = fetchurl {
      url = "https://appcenter-download-api.vercel.app/api/dexterleng/homerow-redux/production/${version}";
      sha256 = "106w6b8lnxhi34fipqfp2nsagsbxbfcwlrzam8pzc399pyq0y9h4";
    };

    sourceRoot = "Homerow.app";

    nativeBuildInputs = [ unzip ];

    unpackPhase = ''
      unzip $src
    '';

    installPhase = ''
      mkdir -p "$out/Applications/${sourceRoot}"
      cp -R . "$out/Applications/${sourceRoot}"
    '';

    meta = with lib; {
      homepage = "https://www.homerow.app/";
      description = "Spotlight for the macOS user interface";
      license = licenses.unfree;
      platforms = platforms.darwin;
      maintainers = [ maintainers.sudosubin ];
    };
  };
}
