{
  fetchFromGitHub,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "grep-app-cli";
  version = "0.1.2";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "grep-app-cli";
    tag = "v${finalAttrs.version}";
    hash = "sha256-z9GEC7Gq4wvzz7T+Ol+WfX6VS2t2MMIqvWEgu9Z4Vps=";
  };

  cargoHash = "sha256-CznefVxFoWnXHIagbqctTKtfoyjh7ofEHfnEwgYeB9w=";

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
