{
  bash,
  fetchFromGitHub,
  fetchPnpmDeps,
  lib,
  nix-update-script,
  nodejs_24,
  pnpm,
  pnpmConfigHook,
  rustPlatform,
  which,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "agent-browser";
  version = "0.26.0";

  src = fetchFromGitHub {
    owner = "vercel-labs";
    repo = "agent-browser";
    tag = "v${finalAttrs.version}";
    hash = "sha256-q3UcFTB8OMOrfx5xcNPtBBAwOxoscwrjGg+y8tdETm0=";
  };

  cargoRoot = "cli";
  buildAndTestSubdir = finalAttrs.cargoRoot;
  cargoHash = "sha256-ENIGFhZ+pXIZvEFUA0No3HpeHtxgJohMgx6F0wNpmO0=";

  nativeBuildInputs = [
    nodejs_24
    pnpm
    pnpmConfigHook
  ];

  nativeCheckInputs = [
    bash
    which
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
    export PATH=${
      lib.makeBinPath [
        bash
        which
      ]
    }:$PATH
  '';

  # Skip tests that are environment-sensitive or timing-sensitive in Nix
  # sandboxes.
  checkFlags = [
    "--skip native::parity_tests::test_all_documented_actions_are_handled"
    "--skip native::parity_tests::test_har_start_stop_without_browser"
    "--skip doctor::helpers::tests::test_new_id_is_unique_per_call"
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
