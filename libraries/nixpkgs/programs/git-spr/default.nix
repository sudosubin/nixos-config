{
  lib,
  buildGoModule,
  fetchFromGitHub,
  nix-update-script,
}:

buildGoModule (finalAttrs: {
  pname = "git-spr";
  version = "0.15.1";

  src = fetchFromGitHub {
    owner = "ejoffe";
    repo = "spr";
    rev = "v${finalAttrs.version}";
    hash = "sha256-477ERmc7hQzbja5qWLI/2zz8gheIEpmMLQSp2EOjjMY=";
  };

  vendorHash = "sha256-vTmzhU/sJ0C8mYuLE8qQQELI4ZwQVv0dsM/ea1mlhFk=";

  postInstall = ''
    mv $out/bin/amend $out/bin/git-amend
    mv $out/bin/reword $out/bin/spr_reword_helper
    mv $out/bin/spr $out/bin/git-spr
  '';

  passthru.updateScript = nix-update-script { };

  meta = with lib; {
    description = "Stacked Pull Requests on GitHub";
    homepage = "https://github.com/ejoffe/spr";
    license = licenses.mit;
    maintainers = with maintainers; [ sudosubin ];
    platforms = platforms.unix;
  };
})
