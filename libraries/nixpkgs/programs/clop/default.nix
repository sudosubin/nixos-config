final: { lib, fetchurl, stdenvNoCC, unzip, ... }@prev:

{
  clop = stdenvNoCC.mkDerivation rec {
    pname = "clop";
    version = "1.4.2";

    src = fetchurl {
      url = "https://files.lowtechguys.com/Clop.zip";
      sha256 = "1m6mxassc9d2758473vngr4gr7idqxc1chyg1mcgflcwawvc42wl";
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
