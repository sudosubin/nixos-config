final: { lib, fetchurl, stdenv, ... }@prev:

let
  inherit (stdenv.hostPlatform) system;

  aarch64-darwin = rec {
    version = "1.66.1";
    src = fetchurl {
      url = "https://github.com/tibeer/vscodium/releases/download/${version}.darwin_arm64/VSCodium.zip";
      sha256 = "sha256-KZ4dy4Cj6H8/2Q9g3r42U/P/UD8YEDITo4h7OEhxWxU=";
    };
  };

in
{
  vscodium = prev.vscodium.overrideAttrs (attrs: rec {
    sourceRoot = if system == "aarch64-darwin" then "" else attrs.sourceRoot;
    version = if system == "aarch64-darwin" then aarch64-darwin.version else attrs.version;
    src = if system == "aarch64-darwin" then aarch64-darwin.src else attrs.src;
    meta = attrs.meta or { } // {
      platforms = attrs.meta.platforms ++ [ "aarch64-darwin" ];
    };
  });
}
