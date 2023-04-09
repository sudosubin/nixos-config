final: { lib, fetchurl, stdenvNoCC, unzip, ... }@prev:

{
  homerow = stdenvNoCC.mkDerivation rec {
    pname = "homerow";
    version = "0.20";

    src = fetchurl {
      url = "https://appcenter-download-api.vercel.app/api/dexterleng/homerow-redux/production/${version}";
      sha256 = "0fppbdk48ddy39rm7spbx2212f2ryj6z808q8205ba9vkj5yys8j";
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
