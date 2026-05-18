{
  fetchFromGitHub,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "figma-agent";
  version = "0.2.1";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "figma-agent";
    tag = "v${finalAttrs.version}";
    hash = "sha256-u3LgZd/wLRjO6cWleV9edI6Wi/yfsZ8N6t8F9iKjCps=";
  };

  cargoHash = "sha256-PyFIh9EBYYmfyiGYle17Ek/kkxePk3aZKyJn5yiJLFk=";

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
