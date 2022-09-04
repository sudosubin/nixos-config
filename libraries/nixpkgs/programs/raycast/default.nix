final: { lib, fetchurl, stdenvNoCC, undmg, ... }@prev:

let
  sha256 = "1fbc32ec046f2ed61e85a1bd5405fe538a101a8a45f28a678a25a4cc79f63e0d";
  version = "1.39.2";

in
{
  raycast = stdenvNoCC.mkDerivation rec {
    pname = "raycast";
    inherit version;

    sourceRoot = "Raycast.app";

    src = fetchurl {
      url = "https://api.raycast.app/v2/download";
      inherit sha256;
    };

    nativeBuildInputs = [ undmg ];

    unpackPhase = ''
      undmg $src
    '';

    installPhase = ''
      mkdir -p "$out/Applications/Raycast.app"
      cp -R . "$out/Applications/Raycast.app"
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
