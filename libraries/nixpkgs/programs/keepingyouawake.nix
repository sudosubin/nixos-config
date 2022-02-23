final: { lib, stdenv, fetchzip, ... }@prev:

{
  keepingyouawake = stdenv.mkDerivation rec {
    pname = "keepingyouawake";
    version = "1.6.2";

    src = fetchzip {
      url = "https://github.com/newmarcel/KeepingYouAwake/releases/download/${version}/KeepingYouAwake-${version}.zip";
      sha256 = "sha256-jRYK5wdxCqUDrG/F8iLd+Cyb6w52I8bbj+q2hQOLZjU=";
    };

    installPhase = ''
      runHook preInstall

      mkdir -p "$out/Applications/KeepingYouAwake.app"
      cp -R . "$out/Applications/KeepingYouAwake.app"

      runHook postInstall
    '';

    meta = with lib; {
      description = "Tool to prevent the system from going into sleep mode";
      homepage = "https://github.com/newmarcel/KeepingYouAwake";
      platforms = platforms.darwin;
      license = licenses.mit;
      maintainers = with maintainers; [ sudosubin ];
    };
  };
}
