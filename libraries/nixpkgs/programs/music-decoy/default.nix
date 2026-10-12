{
  buildSwiftPackage,
  fetchFromGitHub,
  ibtool,
  lib,
  nix-update-script,
  swiftAppBundleHook,
}:

buildSwiftPackage (finalAttrs: {
  pname = "music-decoy";
  version = "1.3";

  src = fetchFromGitHub {
    owner = "FuzzyIdeas";
    repo = "MusicDecoy";
    tag = "v${finalAttrs.version}";
    hash = "sha256-sga62W/aLda68RNjPZw+m7xiEeMTjRHbIt4yY+XO7Os=";
  };

  # No SwiftPM dependencies
  swiftpmManifest = ./Package.swift;
  swiftpmDeps = null;

  nativeBuildInputs = [
    ibtool
    swiftAppBundleHook
  ];

  xcodeProject = "Music Decoy.xcodeproj";
  appResources = [
    "Music/Assets.xcassets"
    "Music/MusicDecoy.sdef"
  ];

  postInstall = ''
    mkdir -p "$out/Applications/Music Decoy.app/Contents/Resources/Base.lproj"
    ibtool --compile "$out/Applications/Music Decoy.app/Contents/Resources/Base.lproj/MainMenu.nib" \
      Music/Base.lproj/MainMenu.xib
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Prevent macOS from launching Music when pressing media Play";
    homepage = "https://github.com/FuzzyIdeas/MusicDecoy";
    changelog = "https://github.com/FuzzyIdeas/MusicDecoy/releases/tag/v${finalAttrs.version}";
    license = lib.licenses.gpl3;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.darwin;
    sourceProvenance = with lib.sourceTypes; [ fromSource ];
  };
})
