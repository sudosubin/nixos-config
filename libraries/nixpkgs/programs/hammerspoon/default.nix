final: { lib, fetchurl, stdenvNoCC, unzip, ... }@prev:

{
  hammerspoon = stdenvNoCC.mkDerivation rec {
    pname = "hammerspoon";
    version = "0.9.100";

    src = fetchurl {
      url = "https://github.com/Hammerspoon/hammerspoon/releases/download/${version}/Hammerspoon-${version}.zip";
      sha256 = "16bkw3j0hi3kfzr4v6v98agnpbx33v63d35iyg595infqw3wikvd";
    };

    sourceRoot = "Hammerspoon.app";

    nativeBuildInputs = [ unzip ];

    unpackPhase = ''
      unzip $src
    '';

    installPhase = ''
      mkdir -p "$out/Applications/${sourceRoot}"
      cp -R . "$out/Applications/${sourceRoot}"
    '';

    meta = with lib; {
      homepage = "http://www.hammerspoon.org/";
      description = "Staggeringly powerful macOS desktop automation with Lua";
      license = licenses.mit;
      platforms = platforms.darwin;
      maintainers = [ maintainers.sudosubin ];
    };
  };
}
