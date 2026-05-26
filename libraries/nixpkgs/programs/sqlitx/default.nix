{
  fetchFromGitHub,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "sqlitx";
  version = "0.1.3";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "sqlitx";
    tag = "v${finalAttrs.version}";
    hash = "sha256-Y3rpbnjmys4Y6AiU8RvFWj6Yv7SjzhJtppJX4pwKdMU=";
  };

  cargoHash = "sha256-9vNemDdRoDeoFpI6QQh/ueRAWYHh6+u1EqOuX02nJ60=";

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
