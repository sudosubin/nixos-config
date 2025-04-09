{
  lib,
  fetchurl,
  stdenvNoCC,
  unzip,
}:

stdenvNoCC.mkDerivation rec {
  pname = "deskpad";
  version = "1.3.2";

  src = fetchurl {
    url = "https://github.com/Stengo/DeskPad/releases/download/v${version}/DeskPad.app.zip";
    sha256 = "1q2sp22qbibrwhaiqjbdbmq9mbj2g5mfsbzbdxx1g4s16q9f5amp";
  };

  sourceRoot = "DeskPad.app";

  nativeBuildInputs = [ unzip ];

  unpackPhase = ''
    unzip $src
  '';

  installPhase = ''
    mkdir -p "$out/Applications/${sourceRoot}"
    cp -R . "$out/Applications/${sourceRoot}"
  '';

  meta = with lib; {
    homepage = "https://github.com/Stengo/DeskPad";
    description = "A virtual monitor for screen sharing";
    license = licenses.mit;
    platforms = platforms.darwin;
    maintainers = [ maintainers.sudosubin ];
  };
}
