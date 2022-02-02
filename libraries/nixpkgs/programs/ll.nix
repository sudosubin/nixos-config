final: { lib, nimPackages, fetchFromGitHub, ... }@prev:

let
  cligen = nimPackages.buildNimPackage rec {
    pname = "cligen";
    version = "1.5.20";
    src = nimPackages.fetchNimble {
      inherit pname version;
      hash = "sha256-zCTOosUf3gkVNXxgFEuSlzqCpMhq6VKqrKYXsQfnTJo=";
    };
  };

  memo = nimPackages.buildNimPackage rec {
    pname = "memo";
    version = "0.3.0";
    src = nimPackages.fetchNimble {
      inherit pname version;
      hash = "sha256-J6CwRMyDleJtKgb0A5sUAM2iHhx9wxCaFB0jKFjDfQs=";
    };
  };
in
{
  ll = nimPackages.buildNimPackage rec {
    pname = "ll";
    version = "0.3.2";

    src = fetchFromGitHub {
      owner = "OldhamMade";
      repo = "ll";
      rev = "${version}";
      sha256 = "sha256-gChrqGLhAnP3vkuEIvWSeUxPKTOgNujdhrXypR49HV0=";
    };

    nimBinOnly = true;
    buildInputs = with nimPackages; [ cligen tempfile memo ];

    meta = with lib; {
      homepage = "https://github.com/OldhamMade/ll";
      description = "A more informative ls, based on k";
      license = licenses.mit;
      platforms = platforms.all;
      maintainers = [ maintainers.sudosubin ];
    };
  };
}
