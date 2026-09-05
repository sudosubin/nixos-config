{
  fetchFromGitHub,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "figma-agent";
  version = "0.2.5";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "figma-agent";
    tag = "v${finalAttrs.version}";
    hash = "sha256-Wh69R0XtLOE6TT3xTkahPGHQN6ukbRU2243STQFuz3c=";
  };

  cargoHash = "sha256-0iSaV6p4tN9Ml1owmVTJxx3pJZHnl7hSKqluRcWw/J0=";

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
