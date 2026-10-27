{ firefox-addons, lib }:

(firefox-addons.buildFirefoxXpiAddon {
  pname = "always-in-container";
  version = "1.0.7";
  addonId = "{a1e9543e-5f73-4763-b376-04e53fd12cbd}";
  url = "https://addons.mozilla.org/firefox/downloads/file/4032840/always_in_container-1.0.7.xpi";
  sha256 = "sha256-bLxjL2P6Sd06q98MSHYRTNigtcjGwn/C2r4ANWCqKrw=";
  meta = {
    description = "Chose a container every time you try to open a page out of a container";
    homepage = "https://github.com/tiansh/always-in-container";
    license = lib.licenses.mpl20;
    platforms = lib.platforms.all;
  };
}).overrideAttrs
  (attrs: {
    passthru = attrs.passthru // {
      updateScript = [
        ../update.sh
        "always-in-container"
      ];
    };
  })
