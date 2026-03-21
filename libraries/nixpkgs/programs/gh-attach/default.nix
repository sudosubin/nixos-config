{
  buildGoModule,
  fetchFromGitHub,
  lib,
  nix-update-script,
}:

buildGoModule (finalAttrs: {
  pname = "gh-attach";
  version = "0.2.0";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "gh-attach";
    rev = "v${finalAttrs.version}";
    hash = "sha256-JoadbTB3ui8G3unOHCLFBl4rtpINTNitalPMV7rNERY=";
  };

  vendorHash = "sha256-AdNwhGVAADT8o1yZ9trL0Kc4XiHhWeinrRT7RGMD8bE=";

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
