{
  buildGoModule,
  fetchFromGitHub,
  lib,
  nix-update-script,
}:

buildGoModule (finalAttrs: {
  pname = "gh-stack";
  version = "0-unstable-2026-05-22";

  src = fetchFromGitHub {
    owner = "github";
    repo = "gh-stack";
    rev = "54aa630be994d94c136df685436be572e35dfa9a";
    hash = "sha256-J+Jy4dx68WOj/OWRnBwKMmTM1rlLUPJEJt8+CFpbFfM=";
  };

  vendorHash = "sha256-iY5sNE8NLak9SaEAFPLsjFKeKE9SdspqjoklB6isLLo=";

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
