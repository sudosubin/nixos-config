final: { lib, fetchurl, stdenvNoCC, unzip, ... }@prev:

{
  homerow = stdenvNoCC.mkDerivation rec {
    pname = "homerow";
    version = "0.21";

    src = fetchurl {
      url = "https://appcenter-download-api.vercel.app/api/dexterleng/homerow-redux/production/${version}";
      sha256 = "0j5dncq5j58q1yrszbly651lf9ywdb23ddi0n45j23hx590sp97l";
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
