{
  fetchFromGitHub,
  installShellFiles,
  lib,
  nix-update-script,
  rustPlatform,
}:

rustPlatform.buildRustPackage (finalAttrs: {
  pname = "querypie-cli";
  version = "0.2.4";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "querypie-cli";
    rev = "v${finalAttrs.version}";
    hash = "sha256-JeBpyT/drOfaRBjGEHiC8JXNw/mC5IYZP0vcUBBYYGM=";
  };

  cargoHash = "sha256-S2tu7BDU2vvshh41f4UxO7lBqJPWNpWw8ik4VUEScWs=";

  nativeBuildInputs = [ installShellFiles ];

  postInstall = ''
    installShellCompletion --cmd querypie \
      --bash <($out/bin/querypie completion bash) \
      --fish <($out/bin/querypie completion fish) \
      --zsh <($out/bin/querypie completion zsh)
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Query QueryPie databases from the terminal with webview authentication";
    homepage = "https://github.com/sudosubin/querypie-cli";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = "querypie";
    platforms = lib.platforms.darwin;
  };
})
