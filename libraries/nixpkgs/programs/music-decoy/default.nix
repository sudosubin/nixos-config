{
  fetchzip,
  lib,
  nix-update-script,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "music-decoy";
  version = "1.3";

  src = fetchzip {
    url = "https://github.com/FuzzyIdeas/MusicDecoy/releases/download/v${finalAttrs.version}/MusicDecoy.zip";
    hash = "sha256-vzIjlcz9W7OSOi8pbTnqoahtWRW2brTeFD0LeLx4ryI=";
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
