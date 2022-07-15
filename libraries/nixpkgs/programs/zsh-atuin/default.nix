final: { lib, stdenv, fzf, python3, ... }@prev:

{
  zsh-atuin = stdenv.mkDerivation rec {
    pname = "zsh-atuin";
    version = "0.1.0";

    src = ./src;

    buildInputs = [ fzf python3 ];

    postPatch = ''
      substituteInPlace bin/zsh-atuin --replace "/usr/bin/env python3" "${python3}/bin/python3"
      substituteInPlace zsh-atuin.plugin.zsh --replace "/usr/bin/env python3" "${python3}/bin/python3"
    '';

    installPhase = ''
      install -Dm755 bin/zsh-atuin $out/share/zsh-atuin/bin/zsh-atuin
      install -D zsh-atuin.plugin.zsh $out/share/zsh-atuin/zsh-atuin.plugin.zsh
    '';

    meta = with lib; {
      homepage = "https://github.com/sudosubin/nixos-config";
      description = "Atuin smart support for zsh shell using fzf";
      license = licenses.mit;
      platforms = platforms.unix;
      maintainers = [ maintainers.sudosubin ];
    };
  };
}
