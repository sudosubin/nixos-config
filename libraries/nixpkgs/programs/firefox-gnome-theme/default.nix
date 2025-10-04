{
  lib,
  stdenv,
  fetchurl,
  unzip,
}:

stdenv.mkDerivation (finalAttrs: {
  pname = "firefox-gnome-theme";
  version = "143";

  src = fetchurl {
    url = "https://github.com/rafaelmardojai/firefox-gnome-theme/archive/refs/tags/v${finalAttrs.version}.zip";
    sha256 = "1qwiqhaharkz6f9hsadlng4wkw5l6zf1k992ylj8q5r9cckkc626";
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
})
