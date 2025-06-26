{
  lib,
  stdenv,
  fetchurl,
  unzip,
}:

stdenv.mkDerivation rec {
  pname = "firefox-gnome-theme";
  version = "137";

  src = fetchurl {
    url = "https://github.com/rafaelmardojai/firefox-gnome-theme/archive/refs/tags/v${version}.zip";
    sha256 = "00xk30nx6ghl5dz7ms8anpnayfa6lh1blqni8qbmr7ng5qs8wzsw";
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
