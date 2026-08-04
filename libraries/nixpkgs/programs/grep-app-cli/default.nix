{
  fetchFromGitHub,
  installShellFiles,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "grep-app-cli";
  version = "0.1.5";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "grep-app-cli";
    tag = "v${finalAttrs.version}";
    hash = "sha256-3/FziNgX5Uw7oSwuA/Sj6rwFMszWlmr8sHtMcWNBXWw=";
  };

  cargoHash = "sha256-CsMXFjaedFqO0T8yEDO4b7LEqzXmVLzd6aS66HeGxYE=";

  nativeBuildInputs = [ installShellFiles ];

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
