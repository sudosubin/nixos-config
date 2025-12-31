{
  lib,
  rustPlatform,
  fetchFromGitHub,
  pkg-config,
  openssl,
  stdenvNoCC,
  nix-update-script,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "claude-code-api";
  version = "0.4.0";

  src = fetchFromGitHub {
    owner = "ZhangHanDong";
    repo = "claude-code-api-rs";
    rev = "v${finalAttrs.version}";
    hash = "sha256-Q2U4WMbOs/rK3MpFczEoqWnj/sOwG/tOHqhsXGpi9RQ=";
  };

  cargoLock = {
    lockFile = ./Cargo.lock;
  };

  postPatch = ''
    ln -s ${./Cargo.lock} Cargo.lock
  '';

  passthru.updateScript = nix-update-script { };

  meta = with lib; {
    description = "A high-performance Rust implementation of an OpenAI-compatible API gateway for Claude Code CLI";
    homepage = "https://github.com/ZhangHanDong/claude-code-api-rs";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.unix;
    mainProgram = "claude-code-api";
  };
})
