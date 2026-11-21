{
  buildGoModule,
  fetchFromGitHub,
  lib,
  nix-update-script,
  go_1_27,
}:

(buildGoModule.override { go = go_1_27; }) (finalAttrs: {
  pname = "gh-attach";
  version = "0.5.1";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "gh-attach";
    rev = "v${finalAttrs.version}";
    hash = "sha256-mXTFqv56y2pwITgVJKuCOuHDZK6F65UU18pN3iz62+I=";
  };

  vendorHash = "sha256-CPlH6NNmBFpoav7vmPbS7P3LbQXNXpQVIP2BIW3XajI=";

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
