{
  fetchzip,
  lib,
  nix-update-script,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "pravka";
  version = "0.1.1";

  src = fetchzip {
    url = "https://github.com/sudosubin/pravka/releases/download/v${finalAttrs.version}/PravkaNerdFontMono-${finalAttrs.version}.zip";
    stripRoot = false;
    hash = "sha256-majYoSfT8hbz4GW2m0T/ukPPZ7fCjDyoLsIQPKKHotw=";
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
