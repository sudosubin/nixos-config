{
  buildGoModule,
  fetchFromGitHub,
  lib,
  nix-update-script,
}:

buildGoModule (finalAttrs: {
  pname = "gh-stack";
  version = "0.0.2-unstable-2026-04-23";

  src = fetchFromGitHub {
    owner = "github";
    repo = "gh-stack";
    rev = "ad21053fe913c29f8542f20685f773076ca09cb6";
    hash = "sha256-auLu1weeBEz4Ao50ByofBSw8GMbtev8ffGY7AFxhrWg=";
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
