final: { lib, fetchurl, stdenvNoCC, unzip, ... }@prev:

{
  homerow = stdenvNoCC.mkDerivation rec {
    pname = "homerow";
    version = "0.19";

    src = fetchurl {
      url = "https://appcenter-download-api.vercel.app/api/dexterleng/homerow-redux/production/${version}";
      sha256 = "1xlppvjba25p832zl73c081yhhly04njl4drxmmdhpilxhvpyyb7";
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
