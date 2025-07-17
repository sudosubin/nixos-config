{
  lib,
  stdenv,
  fetchurl,
  unzip,
}:

stdenv.mkDerivation rec {
  pname = "firefox-gnome-theme";
  version = "140";

  src = fetchurl {
    url = "https://github.com/rafaelmardojai/firefox-gnome-theme/archive/refs/tags/v${version}.zip";
    sha256 = "13ml3sxbwq8n197sh47azkpl1n4jidp6aybqrpnx9l5bb051b9c5";
  };

  nativeBuildInputs = [ unzip ];

  installPhase = ''
    runHook preInstall

    mkdir -p $out
    cp -ra ./configuration ./theme ./icon.svg ./userChrome.css ./userContent.css -t $out

    runHook postInstall
  '';

  meta = {
    description = "GNOME theme for Firefox";
    homepage = "https://github.com/rafaelmardojai/firefox-gnome-theme";
    license = lib.licenses.unlicense;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.all;
  };
}
