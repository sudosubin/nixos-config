final: { lib, stdenv, fetchurl, undmg, ... }@prev:
with lib;

let
  inherit (stdenv.hostPlatform) system;

in
{
  jetbrains.jdk = prev.jetbrains.jdk.overrideDerivation (attrs: { });

  jetbrains.datagrip = prev.jetbrains.datagrip.overrideDerivation (attrs: rec {
    src = (
      if stdenv.isDarwin && system == "aarch64-darwin" then
        (fetchurl {
          url = "https://download.jetbrains.com/datagrip/${attrs.name}-aarch64.dmg";
          sha256 = "sha256-K6ku00NmsRGjm6BjLZHbryMmM/X1VXogjdirdpYXm28=";
        }) else if stdenv.isDarwin then
        (fetchurl {
          url = "https://download.jetbrains.com/datagrip/${attrs.name}.dmg";
          sha256 = lib.fakeSha256;
        }) else
        attrs.src
    );

    sourceRoot = lib.optionalString stdenv.isDarwin "DataGrip.app";

    nativeBuildInputs = (attrs.nativeBuildInputs or [ ])
      ++ (lib.optionals stdenv.isDarwin [ undmg ]);

    installPhase = (if stdenv.isDarwin then ''
      runHook preInstall

      mkdir -p "$out/Applications/${sourceRoot}"
      cp -R . "$out/Applications/${sourceRoot}"

      runHook postInstall
    '' else
      attrs.installPhase);
  });
}
