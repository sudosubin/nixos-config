{
  fetchFromGitHub,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "figma-agent";
  version = "0.2.2";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "figma-agent";
    tag = "v${finalAttrs.version}";
    hash = "sha256-9XqVIwDY4Vhx0mlF0LS5cdGS2qafzQ1ZxYs1CJZE6hQ=";
  };

  cargoHash = "sha256-I4yVab5Uht5sO/k2tMJhtcqcCROu0K3kBOKDEXPWmec=";

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
