{
  buildGoModule,
  fetchFromGitHub,
  lib,
  nix-update-script,
}:

buildGoModule (finalAttrs: {
  pname = "gh-attach";
  version = "0.4.3";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "gh-attach";
    rev = "v${finalAttrs.version}";
    hash = "sha256-+RoHXOJX8Zd99+Ie9jWAEsA/I0rRMkAEYPgayGlSjnY=";
  };

  vendorHash = "sha256-uDt8EnGrikNab3Dq5FQRGO0/b59A7IgW1FOwzcDp2xg=";

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
