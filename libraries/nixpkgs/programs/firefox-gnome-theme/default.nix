{
  lib,
  stdenv,
  fetchurl,
  unzip,
}:

stdenv.mkDerivation (finalAttrs: {
  pname = "firefox-gnome-theme";
  version = "142";

  src = fetchurl {
    url = "https://github.com/rafaelmardojai/firefox-gnome-theme/archive/refs/tags/v${finalAttrs.version}.zip";
    sha256 = "0x77pscl2im409kpkswgah2vqd7n1w0zmff4aa92lv5nnscyk1nf";
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
