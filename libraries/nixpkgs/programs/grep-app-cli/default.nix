{
  fetchFromGitHub,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "grep-app-cli";
  version = "0.1.0";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "grep-app-cli";
    tag = "v${finalAttrs.version}";
    hash = "sha256-pM+Z7oBNFrYmSrL66mFOBcnpdSUB+VvOWCuP8bhNlHI=";
  };

  cargoHash = "sha256-hiIr02G0G2jmHvxRrijS/xKnRams5XxZBMoe5GwpB1I=";

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
