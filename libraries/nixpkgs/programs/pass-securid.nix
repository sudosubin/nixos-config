final: { lib, stdenv, fetchFromGitHub, stoken, ... }@prev:

let
  rev = "cd32e2d58db780fc2f0bf7d98742380154bd541d";
in
{
  pass-securid = stdenv.mkDerivation rec {
    pname = "pass-securid";
    version = "${builtins.substring 0 8 rev}";

    src = fetchFromGitHub {
      owner = "sudosubin";
      repo = "pass-securid";
      rev = "${rev}";
      sha256 = "sha256-HaOGaioeL8V8VNUBNzzdpsAz7LTOyFDkacmq82Yyt4E=";
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
