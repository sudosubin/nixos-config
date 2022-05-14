dfinal: { lib, stdenv, fetchFromGitHub, stoken, ... }@prev:

let
  rev = "99e5da3fa7e2b5c613a3c275de182b82facd54a5";
in
{
  pass-securid = stdenv.mkDerivation rec {
    pname = "pass-securid";
    version = "0.1.1";

    src = fetchFromGitHub {
      owner = "sudosubin";
      repo = "pass-securid";
      rev = "v${version}";
      sha256 = "sha256-FF5FIjQTYtNkuwdsyfcQxPOKg9loP7IDKU/nQAiVd1k=";
    };

    buildInputs = [ stoken ];
    dontBuild = true;

    patchPhase = ''
      sed -i -e 's|STOKEN=\$(command -v stoken)|STOKEN=${stoken}/bin/stoken|' src/securid.bash
    '';

    installFlags = [
      "PREFIX=$(out)"
      "BASH_COMPLETION_DIR=$(out)/share/bash-completion/completions"
    ];

    meta = with lib; {
      homepage = "https://github.com/sudosubin/pass-securid";
      description = "A pass extension for managing RSA SecurIDs";
      platforms = platforms.unix;
      license = licenses.gpl3Plus;
      maintainers = with maintainers; [ sudosubin ];
    };
  };
}
