{
  buildGoModule,
  fetchFromGitHub,
  lib,
  nix-update-script,
}:

buildGoModule (finalAttrs: {
  pname = "gh-stack";
  version = "0.0.2-unstable-2026-04-22";

  src = fetchFromGitHub {
    owner = "github";
    repo = "gh-stack";
    rev = "a853a21e3509dc74e570184d1c41cf5de907e791";
    hash = "sha256-W5oTVJf1nIK2wCs2o4DTVGprVCEFSk9MG/jOzSMYJD4=";
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
