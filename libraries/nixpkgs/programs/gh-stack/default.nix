{
  buildGoModule,
  fetchFromGitHub,
  lib,
  nix-update-script,
}:

buildGoModule (finalAttrs: {
  pname = "gh-stack";
  version = "0.0.1-unstable-2026-04-14";

  src = fetchFromGitHub {
    owner = "github";
    repo = "gh-stack";
    rev = "5c1fe16868c5a6e55ab008b111b1dcfab0967b2b";
    hash = "sha256-rwOX3KQMMk3AYNYOoAhr7uErYd8zwthwZHXj8D5ryd8=";
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
