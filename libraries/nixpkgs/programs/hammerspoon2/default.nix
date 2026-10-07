{
  fetchzip,
  lib,
  nix-update-script,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "hammerspoon2";
  version = "0.0.13";

  src = fetchzip {
    url = "https://github.com/cmsj/Hammerspoon2/releases/download/${finalAttrs.version}/Hammerspoon.2.zip";
    hash = "sha256-ePjoOSrN5TcKSM6824dJBvmqu2dTHNxEuB5TU5cD23U=";
    stripRoot = false;
  };

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/Applications"
    cp -R "Hammerspoon 2.app" "$out/Applications/"
    runHook postInstall
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "A modernized rewrite of Hammerspoon - a powerful macOS application for automating your Mac using JavaScript.";
    homepage = "https://github.com/cmsj/Hammerspoon2";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.darwin;
  };
})
