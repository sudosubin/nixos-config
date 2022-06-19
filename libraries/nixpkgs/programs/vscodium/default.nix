final: { lib, stdenv, ... }@prev:
with lib;

let
  stylesheet = {
    ".quick-input-widget" = "font-family: monospace !important;";
    ".search-view .search-widgets-container" = "font-family: monospace !important;";
    ".monaco-list-rows, .monaco-findInput" = "font-family: monospace !important;";
  };

  toCss = stylesheet: strings.concatStrings (attrsets.mapAttrsToList (key: value: "${key}{${value}}") stylesheet);

in
{
  vscodium = prev.vscodium.overrideDerivation (attrs: rec {
    nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ [ prev.nodejs ];

    resources = if stdenv.isDarwin then "Contents/Resources" else "resources";

    preInstall = ''
      ${attrs.preInstall or ""}

      recalculateChecksum() {
        filename="$1"
        filename_escaped="$(echo "$filename" | sed "s/\//\\\\\//g" | sed "s/\./\\\\\./g")"

        checksum=$(node -e """
          const crypto = require('crypto');
          const fs = require('fs');

          const contents = fs.readFileSync('$resources/app/out/$filename');
          console.log(crypto.createHash('md5').update(contents).digest('base64').replace(/=+$/, '''));
        """)

        sed -r "s/\"($filename_escaped)\": \"(.*)\"/\"\1\": \"''${checksum//\//\\\/}\"/" \
            -i "$resources/app/product.json"
      }

      echo "${toCss stylesheet}" >> $resources/app/out/vs/workbench/workbench.desktop.main.css
      recalculateChecksum "vs/workbench/workbench.desktop.main.css"
    '';
  });
}
