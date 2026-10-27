{ firefox-addons, lib }:

(firefox-addons.buildFirefoxXpiAddon {
  pname = "trancyfordesktop";
  version = "7.8.1";
  addonId = "{29f42579-9618-4dc7-8647-eaad7cd3343e}";
  url = "https://addons.mozilla.org/firefox/downloads/file/4727684/trancyfordesktop-7.8.1.xpi";
  sha256 = "sha256-fTXVBQnmtFWy9UU3EgDkBVPjb9FzwAZuWdIY+YIunc4=";
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
