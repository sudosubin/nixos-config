{ firefox-addons, lib }:

(firefox-addons.buildFirefoxXpiAddon {
  pname = "trancyfordesktop";
  version = "7.9.7";
  addonId = "{29f42579-9618-4dc7-8647-eaad7cd3343e}";
  url = "https://addons.mozilla.org/firefox/downloads/file/5206225/trancyfordesktop-7.9.7.xpi";
  sha256 = "sha256-B5Cktugb40AYRgX1PcNFGCh3eMSVl88pTyoA9qt5Gvc=";
  meta = {
    description = "Bilingual subtitles for YouTube, Disney+ and more, plus an AI translator for websites";
    homepage = "https://manual.trancy.org";
    license = lib.licenses.mpl20;
    platforms = lib.platforms.all;
  };
}).overrideAttrs
  (attrs: {
    passthru = attrs.passthru // {
      updateScript = [
        ../update.sh
        "trancyfordesktop"
      ];
    };
  })
