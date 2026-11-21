{ firefox-addons, lib }:

(firefox-addons.buildFirefoxXpiAddon {
  pname = "trancyfordesktop";
  version = "7.9.8";
  addonId = "{29f42579-9618-4dc7-8647-eaad7cd3343e}";
  url = "https://addons.mozilla.org/firefox/downloads/file/5227769/trancyfordesktop-7.9.8.xpi";
  sha256 = "sha256-XDaIiTonRhbHp634yYhjCpiPu/t7c4OocwHMV0G6OgA=";
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
