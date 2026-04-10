{
  fetchFromGitHub,
  fetchPnpmDeps,
  lib,
  nix-update-script,
  nodejs_24,
  pnpm,
  pnpmConfigHook,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "agent-browser";
  version = "0.25.3";

  src = fetchFromGitHub {
    owner = "vercel-labs";
    repo = "agent-browser";
    tag = "v${finalAttrs.version}";
    hash = "sha256-9wunuGSsxKqy9h3MMahW3hzZ+5iJrz/SotPRRGDu+kg=";
  };

  cargoRoot = "cli";
  buildAndTestSubdir = finalAttrs.cargoRoot;
  cargoHash = "sha256-vCxv2vKSWj5kIWhzWlbWNfEHrxnSg1i0nUBq6hWoQlM=";

  nativeBuildInputs = [
    nodejs_24
    pnpm
    pnpmConfigHook
  ];

  pnpmWorkspaces = [ "dashboard" ];

  pnpmDeps = fetchPnpmDeps {
    inherit (finalAttrs)
      pname
      version
      src
      pnpmWorkspaces
      ;
    fetcherVersion = 2;
    hash = "sha256-M29MITaUUYPvg7h8A0oGrrT9oerBE97RFd6apiwOlBM=";
  };

  preBuild = ''
    export NEXT_TELEMETRY_DISABLED=1
    pnpm --dir packages/dashboard build
  '';

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
