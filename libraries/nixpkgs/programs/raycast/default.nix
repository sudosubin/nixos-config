final: { lib, fetchurl, stdenvNoCC, undmg, ... }@prev:

{
  raycast = stdenvNoCC.mkDerivation rec {
    pname = "raycast";
    version = "1.49.2";

    src = fetchurl {
      url = "https://releases.raycast.com/download";
      sha256 = "05fshljvi9hkwj32ynv5ljs7al91ff4fdz1g8xqlhrl22i4yxsyx";
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
