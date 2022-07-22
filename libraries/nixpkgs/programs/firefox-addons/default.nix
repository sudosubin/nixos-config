final: { lib, fetchurl, ... }@prev:

rec {
  firefox-utils = {
    addonFromFirefoxAddons = lib.makeOverridable (
      { stdenv ? prev.stdenv, pname, version, addonId, src, meta ? { }, ... }:
      stdenv.mkDerivation {
        name = "${pname}-${version}";

        inherit src meta;

        buildCommand = ''
          dst="$out/share/mozilla/extensions/{ec8030f7-c20a-464f-9b0e-13a3a9e97384}"
          mkdir -p "$dst"
          install -m644 "$src" "$dst/${addonId}.xpi"
        '';
      }
    );
  };

  firefox-addons = {
    _1password-x-password-manager = firefox-utils.addonFromFirefoxAddons {
      pname = "1password-x-password-manager";
      version = "2.3.7";
      addonId = "{d634138d-c276-4fc8-924b-40a0ea21d284}";
      src = fetchurl {
        url = "https://addons.mozilla.org/firefox/downloads/file/3972472/1password_x_password_manager-2.3.7.xpi";
        sha256 = "0m6ksv93dh24m8rcvah2ymcqdfni0ma3aniwv01aiyh5blhy7bls";
      };
    };

    darkreader = firefox-utils.addonFromFirefoxAddons {
      pname = "darkreader";
      version = "4.9.52";
      addonId = "addon@darkreader.org";
      src = fetchurl {
        url = "https://addons.mozilla.org/firefox/downloads/file/3968561/darkreader-4.9.52.xpi";
        sha256 = "0vdlh1nljmfrimz63w2nafa0ghhzbixdbaqvqcikxvm6185fp3a1";
      };
    };

    react-devtools = firefox-utils.addonFromFirefoxAddons {
      pname = "react-devtools";
      version = "4.25.0";
      addonId = "@react-devtools";
      src = fetchurl {
        url = "https://addons.mozilla.org/firefox/downloads/file/3975827/react_devtools-4.25.0.xpi";
        sha256 = "18sm46ch4pij90wcgvhqdbjliv02j5j16abj11j9rjgd8i8cniw5";
      };
    };

    ublock-origin = firefox-utils.addonFromFirefoxAddons {
      pname = "ublock-origin";
      version = "1.43.0";
      addonId = "uBlock0@raymondhill.net";
      src = fetchurl {
        url = "https://addons.mozilla.org/firefox/downloads/file/3961087/ublock_origin-1.43.0.xpi";
        sha256 = "05laq4wlzs4jhngkbrx65c2rjvks3l9zyc1q150hixf4vyl4ybdb";
      };
    };
  };
}
