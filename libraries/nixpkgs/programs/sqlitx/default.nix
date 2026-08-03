{
  fetchFromGitHub,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "sqlitx";
  version = "0.1.5";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "sqlitx";
    tag = "v${finalAttrs.version}";
    hash = "sha256-OtrnyuncHffaGLRtxHPZyhb57F7w5fXltqs5racEafM=";
  };

  cargoHash = "sha256-7CHPKqDiUlGDmaALiX2DC6kFhxXOktpmByyd5Oqt9t8=";

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "fzf-powered connection picker for sqlit";
    homepage = "https://github.com/sudosubin/sqlitx";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = "sqlitx";
    platforms = lib.platforms.unix;
  };
})
