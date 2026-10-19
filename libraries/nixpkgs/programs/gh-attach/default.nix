{
  buildGoModule,
  fetchFromGitHub,
  lib,
  nix-update-script,
  go_1_27,
}:

(buildGoModule.override { go = go_1_27; }) (finalAttrs: {
  pname = "gh-attach";
  version = "0.5.0";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "gh-attach";
    rev = "v${finalAttrs.version}";
    hash = "sha256-O3hocWsMvPGLWZAJhdehQM36chM7bq90wKuZFTFn4K0=";
  };

  vendorHash = "sha256-1Jp5gkwt97Wy+7nOp55Io2Rrj5TzObNNo9J/hOzgQ3k=";

  subPackages = [ "cmd/gh-attach" ];

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "GitHub user attachment upload CLI for gh (GitHub CLI)";
    homepage = "https://github.com/sudosubin/gh-attach";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.unix;
    mainProgram = "gh-attach";
  };
})
