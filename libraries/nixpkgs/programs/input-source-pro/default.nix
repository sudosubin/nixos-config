{ lib, fetchurl, stdenvNoCC, _7zz }:

stdenvNoCC.mkDerivation rec {
  pname = "input-source-pro";
  version = "2.5.0-beta";

  src = fetchurl {
    url = "https://inputsource.pro/beta/Input_Source_Pro_${version}.dmg";
    sha256 = "1x1cplx812hchiycl0i6m3lqcq8jhk7n34vwxd5wnl6s7a1h9px2";
  };

  sourceRoot = "Input Source Pro.app";

  nativeBuildInputs = [ _7zz ];

  installPhase = ''
    mkdir -p "$out/Applications/${sourceRoot}"
    cp -R . "$out/Applications/${sourceRoot}"
  '';

  meta = with lib; {
    homepage = "https://inputsource.pro/";
    description = "Switch and track your input sources with ease";
    license = licenses.unfree;
    platforms = platforms.darwin;
    maintainers = [ maintainers.sudosubin ];
  };
}
