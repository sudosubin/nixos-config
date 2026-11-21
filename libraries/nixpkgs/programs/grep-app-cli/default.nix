{
  fetchFromGitHub,
  installShellFiles,
  lib,
  nix-update-script,
  oniguruma,
  pkg-config,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "grep-app-cli";
  version = "0.1.6";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "grep-app-cli";
    tag = "v${finalAttrs.version}";
    hash = "sha256-r13/X4s4v7YRn9dHHYfevBz+k3RCGy4h3KLb/YyDMeo=";
  };

  cargoHash = "sha256-i8y4lTRaTu1bxFP1/JlCgZNFLmMVSK0+zuRZNs7HK6U=";

  nativeBuildInputs = [
    installShellFiles
    pkg-config
  ];

  buildInputs = [ oniguruma ];

  postInstall = ''
    installShellCompletion --cmd grep-app-cli \
      --bash <($out/bin/grep-app-cli completion bash) \
      --fish <($out/bin/grep-app-cli completion fish) \
      --zsh <($out/bin/grep-app-cli completion zsh)
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "CLI for grep.app — search code across 1M+ public GitHub repos";
    homepage = "https://github.com/sudosubin/grep-app-cli";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.unix;
    mainProgram = "grep-app-cli";
  };
})
