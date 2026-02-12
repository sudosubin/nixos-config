{
  fetchzip,
  lib,
  nix-update-script,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "music-decoy";
  version = "1.1";

  src = fetchzip {
    url = "https://github.com/FuzzyIdeas/MusicDecoy/releases/download/v${finalAttrs.version}/MusicDecoy.zip";
    hash = "sha256-Aew9i9PXd3mm/wePXReUXKZxx2VcPIFlwFzQTwOywY4=";
  };

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/Applications/Music Decoy.app"
    cp -R . "$out/Applications/Music Decoy.app"
    runHook postInstall
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Prevent macOS from launching Music when pressing media Play";
    homepage = "https://github.com/FuzzyIdeas/MusicDecoy";
    license = lib.licenses.gpl3;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.darwin;
  };
})
