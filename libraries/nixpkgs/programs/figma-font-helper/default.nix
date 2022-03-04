final: { lib, fetchFromGitHub, rustPlatform, freetype, ... }@prev:

let
  rev = "7139c5d8e3a5d988ce2dedf5a7cfd241ce03c563";

in
{
  figma-font-helper = rustPlatform.buildRustPackage rec {
    pname = "figma-font-helper";
    version = lib.substring 0 7 rev;

    src = fetchFromGitHub {
      inherit rev;
      owner = "Figma-Linux";
      repo = "figma-linux-font-helper";
      sha256 = "sha256-H2GRmGr874EJMXG8f4qf/c0mbrrnjLzLyuhvjSGnWqY=";
    };

    patches = [ ./config.patch ./log.patch ];

    cargoSha256 = "sha256-69WEzDh90UFdIvOmpM+H30ayC7wClf0jLoI1vH5mbp4=";

    buildInputs = [ freetype ];

    postInstall = ''
      mv $out/bin/font_helper $out/bin/fonthelper
    '';

    meta = with lib; {
      homepage = "https://github.com/Figma-Linux/figma-linux-font-helper";
      description = "Font Helper for Figma for Linux x64 platform";
      license = licenses.gpl2;
      platforms = platforms.linux;
      maintainers = [ maintainers.sudosubin ];
    };
  };
}
