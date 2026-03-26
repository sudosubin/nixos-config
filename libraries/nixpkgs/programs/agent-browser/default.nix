{
  fetchFromGitHub,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "agent-browser";
  version = "0.22.3";

  src = fetchFromGitHub {
    owner = "vercel-labs";
    repo = "agent-browser";
    tag = "v${finalAttrs.version}";
    hash = "sha256-Bd3T6WHOMrnMOn3HF9Bk5K8vsUW/fZlbP0496zhiVWc=";
  };

  sourceRoot = "${finalAttrs.src.name}/cli";

  cargoHash = "sha256-RgtDrL7556TaVTAtFbvgx3xNigVAJ/VSglqOl43zODM=";

  # tests write under $HOME/.agent-browser/auth.
  preCheck = ''
    export HOME="$TMPDIR/home"
    mkdir -p "$HOME"
  '';

  # Skip tests that auto-launch host Chrome, which makes checks non-hermetic
  # and flaky/slow in Nix builds.
  checkFlags = [
    "--skip native::parity_tests::test_all_documented_actions_are_handled"
    "--skip native::parity_tests::test_har_start_stop_without_browser"
  ];

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
