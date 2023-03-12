final: { lib, fetchurl, stdenvNoCC, undmg, ... }@prev:

{
  raycast = stdenvNoCC.mkDerivation rec {
    pname = "raycast";
    version = "1.48.8";

    src = fetchurl {
      url = "https://releases.raycast.com/download";
      sha256 = "0zfx9yjn30kiqgf94xsjnadsyi3w45w4izm809n644h8bckjkkv2";
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
