{
  buildGoModule,
  fetchFromGitHub,
  lib,
  nix-update-script,
}:

buildGoModule (finalAttrs: {
  pname = "gh-stack";
  version = "0.0.2-unstable-2026-05-05";

  src = fetchFromGitHub {
    owner = "github";
    repo = "gh-stack";
    rev = "de00856fdeea80f8eaac9762d7f653a1d69bb852";
    hash = "sha256-yQ3I5Orlnd+zt10XW8fUtdLR3yp1Lhf9pCeT91ZXN3w=";
  };

  vendorHash = "sha256-JnuqORtdW+xz8pAGAFXdjRey8jCEj+miJiyfY7gzRSU=";

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
