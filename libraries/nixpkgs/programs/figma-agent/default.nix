{
  fetchFromGitHub,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "figma-agent";
  version = "0.2.4";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "figma-agent";
    tag = "v${finalAttrs.version}";
    hash = "sha256-PoLOxRmzZZTY+7EEYab3Qk+aoyJ7BXClpNe5iSH4hAE=";
  };

  cargoHash = "sha256-hgMx/4/zKds9KUmkXe15x1Vsq/YPmCng76l474yI6IE=";

  passthru.updateScript = nix-update-script { };

  meta = {
    mainProgram = "figma-agent";
    description = "Local font helper for Figma, Linux and macOS";
    homepage = "https://github.com/sudosubin/figma-agent";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.unix;
  };
})
