{
  fetchFromGitHub,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "sqlitx";
  version = "0.1.0";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "sqlitx";
    tag = "v${finalAttrs.version}";
    hash = "sha256-8moeMaNw2WUEdaWtrSK6JcdrF4iv/+r+UlaKjdnXDMU=";
  };

  cargoHash = "sha256-XlzjutQCKlEW/9KKbh3oGK6jCn8KYe9DloPGN/RnX2o=";

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
