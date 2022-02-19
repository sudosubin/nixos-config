final: { lib, stdenv, fetchurl, undmg, ... }@prev:
with lib;

let
  inherit (stdenv.hostPlatform) system;

in
{
  jetbrains.datagrip = prev.jetbrains.datagrip.overrideDerivation (attrs: rec {
    src = fetchurl (if stdenv.isDarwin && system == "aarch64-darwin" then {
      url = "https://download.jetbrains.com/datagrip/${attrs.name}-aarch64.dmg";
      sha256 = "sha256-ene6n85Wx4Guak/GXqq0vMEHgLa9Z5sE10FGcZ5CiQo=";
    } else if stdenv.isDarwin then {
      url = "https://download.jetbrains.com/datagrip/${attrs.name}.dmg";
      sha256 = lib.fakeSha256;
    } else
      attrs.src
    );

    sourceRoot = "DataGrip.app";

    nativeBuildInputs = (attrs.nativeBuildInputs or [ ]) ++ (lib.optionals stdenv.isDarwin [ undmg ]);

    installPhase = lib.optional stdenv.isDarwin ''
      runHook preInstall

      mkdir -p "$out/Applications/${sourceRoot}"
      cp -R . "$out/Applications/${sourceRoot}"

      runHook postInstall
    '';
  });
}
