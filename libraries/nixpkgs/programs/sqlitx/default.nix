{
  fetchFromGitHub,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "sqlitx";
  version = "0.1.2";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "sqlitx";
    tag = "v${finalAttrs.version}";
    hash = "sha256-chy79UVGqWaS4iwo/Fu23gn/EH4xaQBXIli7NizvKCQ=";
  };

  cargoHash = "sha256-6RRrE6KfyMvyEOqRbtn0M/cyH+P8nm77qFetkGP19kc=";

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
