{
  fetchFromGitHub,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "deepwiki-cli";
  version = "0.1.1";

  src = fetchFromGitHub {
    owner = "hamsurang";
    repo = "deepwiki-cli";
    tag = "v${finalAttrs.version}";
    hash = "sha256-6fY6gNJMDV6VeuauT4HGUupWGnZKl44ZT12TqAuTO/k=";
  };

  cargoHash = "sha256-/979PeZAs2cDLAK+YCnT3iTbFnL3PDwU2BqyikWXRDA=";

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
