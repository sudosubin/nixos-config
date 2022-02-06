final: { lib, stdenv, fetchFromGitHub, stoken, ... }@prev:

let
  rev = "99e5da3fa7e2b5c613a3c275de182b82facd54a5";
in
{
  pass-securid = stdenv.mkDerivation rec {
    pname = "pass-securid";
    version = "${builtins.substring 0 8 rev}";

    src = fetchFromGitHub {
      owner = "sudosubin";
      repo = "pass-securid";
      rev = "${rev}";
      sha256 = "sha256-MS+s2GiAgIBzw4jn497aAG8JoGdKhNvY3oTc8J5+PDQ=";
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
      description = "A pass extension for managing RSA SecurIDs";
      homepage = "https://github.com/sudosubin/pass-securid";
      platforms = platforms.unix;
      license = licenses.gpl3Plus;
      maintainers = with maintainers; [ sudosubin ];
    };
  };
}
