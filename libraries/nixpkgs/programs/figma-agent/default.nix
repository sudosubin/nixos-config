{
  fetchFromGitHub,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "figma-agent";
  version = "0.2.3";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "figma-agent";
    tag = "v${finalAttrs.version}";
    hash = "sha256-TxWoj8SgkF7eB6xdl4N9fk/NRk8XEPQCAtMuP0bjeOk=";
  };

  cargoHash = "sha256-NJzyyiqIfCj4X1Z9DPBWA95OCimvmwbNX9d60kNt7uQ=";

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
