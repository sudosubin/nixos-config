final: { lib, fetchurl, stdenvNoCC, undmg, ... }@prev:

{
  raycast = stdenvNoCC.mkDerivation rec {
    pname = "raycast";
    version = "1.44.0";

    src = fetchurl {
      url = "https://api.raycast.app/v2/download";
      sha256 = "12xdvqqjbbyaiivlqc3br51nb8181ylavlgryzb655lwkg3jshyz";
    };

    sourceRoot = "Raycast.app";

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
