{
  fetchFromGitHub,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "grep-app-cli";
  version = "0.1.1";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "grep-app-cli";
    tag = "v${finalAttrs.version}";
    hash = "sha256-adOaAhZkRvvyLZ39PcqG0jBULjcaEoVhTmyoKAaAiD4=";
  };

  cargoHash = "sha256-P7wCDXF/x3qeif8nDsBEMo22QibM3hDx2Rirdn+5wMc=";

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "CLI for grep.app — search code across 1M+ public GitHub repos";
    homepage = "https://github.com/sudosubin/grep-app-cli";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.unix;
    mainProgram = "grep-app-cli";
  };
})
