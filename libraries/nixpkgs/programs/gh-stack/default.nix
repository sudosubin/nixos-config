{
  buildGoModule,
  fetchFromGitHub,
  lib,
  nix-update-script,
}:

buildGoModule (finalAttrs: {
  pname = "gh-stack";
  version = "0-unstable-2026-04-13";

  src = fetchFromGitHub {
    owner = "github";
    repo = "gh-stack";
    rev = "e06284ff5cc134d7432017c10e4ca17212ba1a21";
    hash = "sha256-8iCixuRXn8DaUi1u/sllDfWGIgx2or7VcWvwQv9zinE=";
  };

  vendorHash = "sha256-s85Lz6yfY1TiIFPolU1qESDyw8XoBORyuOMdiHj6Grc=";

  subPackages = [ "." ];

  ldflags = [ "-X=github.com/github/gh-stack/cmd.Version=${finalAttrs.version}" ];

  passthru.updateScript = nix-update-script {
    extraArgs = [ "--version=branch" ];
  };

  meta = {
    description = "GitHub Stacked PRs";
    homepage = "https://github.com/github/gh-stack";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.unix;
    mainProgram = "gh-stack";
  };
})
