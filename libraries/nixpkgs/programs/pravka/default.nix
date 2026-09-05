{
  fetchzip,
  lib,
  nix-update-script,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "pravka";
  version = "0.1.3";

  src = fetchzip {
    url = "https://github.com/sudosubin/pravka/releases/download/v${finalAttrs.version}/PravkaNerdFontMono-${finalAttrs.version}.zip";
    stripRoot = false;
    hash = "sha256-Bdu0bxrPkE4sI2UuLx+zjW1mTF5BwBbv+HesYqFUr8o=";
  };

  installPhase = ''
    runHook preInstall
    find . -name "*.otf" -exec install -Dm644 -t "$out/share/fonts/opentype" {} +
    runHook postInstall
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Free monospace font tuned to match PragmataPro, Nerd Font Mono patched (Iosevka-based)";
    homepage = "https://github.com/sudosubin/pravka";
    license = lib.licenses.ofl;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.all;
  };
})
