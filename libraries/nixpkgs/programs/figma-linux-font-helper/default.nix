{
  fetchFromGitHub,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "figma-linux-font-helper";
  version = "0.1.8";

  src = fetchFromGitHub {
    owner = "Figma-Linux";
    repo = "figma-linux-font-helper";
    rev = "v${finalAttrs.version}";
    hash = "sha256-0Akdz5Bc15Ph9B/2nvvYwAAq1hjV6+k7eY9+W2n8ODo=";
  };

  cargoPatches = [ ./fix-cargo-lock.patch ];
  cargoHash = "sha256-hD55ROihp827iK7UL4mkZFCKbyv1zvivj6Jcr+wqV7c=";

  postInstall = ''
    ln -s "$out/bin/font_helper" "$out/bin/fonthelper"
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    mainProgram = "fonthelper";
    description = "Local font helper for Figma on Linux";
    homepage = "https://github.com/Figma-Linux/figma-linux-font-helper";
    license = lib.licenses.gpl2Only;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.linux;
  };
})
