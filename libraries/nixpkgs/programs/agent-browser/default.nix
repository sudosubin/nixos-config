{
  fetchFromGitHub,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "agent-browser";
  version = "0.21.4";

  src = fetchFromGitHub {
    owner = "vercel-labs";
    repo = "agent-browser";
    tag = "v${finalAttrs.version}";
    hash = "sha256-T+IiizT1e5nuH6EqROn0b/w3H1OShWTTHUqD7tZJDkw=";
  };

  sourceRoot = "${finalAttrs.src.name}/cli";

  cargoHash = "sha256-E0QbXOC4h3MfYeDR+eSW9J4smnAPOf48PhmVK/pPZ+E=";

  # tests write under $HOME/.agent-browser/auth.
  preCheck = ''
    export HOME="$TMPDIR/home"
    mkdir -p "$HOME"
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Headless browser automation CLI for AI agents";
    homepage = "https://github.com/vercel-labs/agent-browser";
    changelog = "https://github.com/vercel-labs/agent-browser/blob/main/CHANGELOG.md";
    license = lib.licenses.asl20;
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = "agent-browser";
    platforms = lib.platforms.unix;
  };
})
