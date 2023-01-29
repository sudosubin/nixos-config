final: { lib, fetchurl, stdenvNoCC, undmg, ... }@prev:

{
  raycast = stdenvNoCC.mkDerivation rec {
    pname = "raycast";
    version = "1.46.0";

    src = fetchurl {
      url = "https://releases.raycast.com/download";
      sha256 = "1w8hnh1miiwvckhg7ipp0lgv9l85b4wmkma7mjvxrv07szicbqj2";
    };

    sourceRoot = "Raycast.app";

    nativeBuildInputs = [ undmg ];

    unpackPhase = ''
      undmg $src
    '';

    installPhase = ''
      mkdir -p "$out/Applications/${sourceRoot}"
      cp -R . "$out/Applications/${sourceRoot}"
    '';

    meta = with lib; {
      homepage = "https://www.raycast.com/";
      description = "Control your tools with a few keystrokes";
      license = licenses.unfree;
      platforms = platforms.darwin;
      maintainers = [ maintainers.sudosubin ];
    };
  };
}
