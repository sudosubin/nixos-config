final: { lib, fetchurl, stdenvNoCC, unzip, ... }@prev:

{
  clop = stdenvNoCC.mkDerivation rec {
    pname = "clop";
    version = "1.4.2";

    src = fetchurl {
      url = "https://files.lowtechguys.com/Clop.zip";
      sha256 = "1kdc88jg1zkb0086g8ag6ic6d43jxbrvr1zmnq4hlq82dc2c58iq";
    };

    sourceRoot = "Clop.app";

    nativeBuildInputs = [ unzip ];

    unpackPhase = ''
      unzip $src
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
