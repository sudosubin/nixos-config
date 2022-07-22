final: { lib, stdenv, nerd-font-patcher, ... }@prev:

{
  pragmatapro = stdenv.mkDerivation rec {
    pname = "pragmatapro";
    version = "0.829";

    src = builtins.fetchGit {
      url = "ssh://git@github.com/sudosubin/pragmatapro.git";
      rev = "e8d972e226f64f844c710ae83272faa29c7cfbef";
    };

    nativeBuildInputs = [ nerd-font-patcher ];

    preInstall = ''
      mkdir -p $out/share/fonts/opentype
    '';

    installPhase = ''
      runHook preInstall

      find -name "PragmataPro_Mono*.otf" ! -name "*_liga_*" \
        -exec nerd-font-patcher -s -q -c --no-progressbars -out "$out/share/fonts/opentype" {} \;
    '';

    meta = with lib; {
      homepage = "https://fsd.it/shop/fonts/pragmatapro/";
      description = ''
        Condensed monospaced font optimized for screen, designed by Fabrizio
        Schiavi to be the ideal font for coding, math and engineering
      '';
      licence = licences.unfree;
      platforms = platforms.all;
      maintainers = [ maintainers.sudosubin ];
    };
  };
}
