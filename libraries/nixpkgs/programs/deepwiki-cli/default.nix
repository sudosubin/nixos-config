{
  fetchFromGitHub,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "deepwiki-cli";
  version = "0.2.0";

  src = fetchFromGitHub {
    owner = "hamsurang";
    repo = "deepwiki-cli";
    tag = "v${finalAttrs.version}";
    hash = "sha256-dUJ/cEefleHtGIAL363gNs9l/UIr7P6frPfp+aWVRRA=";
  };

  cargoHash = "sha256-LKOQjbevshaVI6a37nXTd/g6dnXDwtrfocZ9GRgRu1E=";

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "cli tools for deepwiki";
    homepage = "https://github.com/hamsurang/deepwiki-cli";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.unix;
    mainProgram = "deepwiki-cli";
  };
})
