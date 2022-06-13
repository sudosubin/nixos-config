final: { lib, fetchFromGitHub, rustPlatform, freetype, ... }@prev:

let
  rev = "49efd1a37ea690378e88278c2a744dcf66210b23";

in
{
  figma-font-helper = rustPlatform.buildRustPackage rec {
    pname = "figma-font-helper";
    version = lib.substring 0 7 rev;

    src = fetchFromGitHub {
      inherit rev;
      owner = "Figma-Linux";
      repo = "figma-linux-font-helper";
      sha256 = "sha256-U66UPuNpbGqmrTlYSK+pGfejTaly3VIyIazghu/Xvco=";
    };

    patches = [ ./config.patch ./main.patch ];

    cargoSha256 = "sha256-9WtSxQJIN/rIXBMydeknJiwDXxvK88zx0DvX+j0SEvg=";

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
