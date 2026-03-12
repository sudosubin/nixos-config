{
  buildGoModule,
  fetchFromGitHub,
  installShellFiles,
  lib,
  nix-update-script,
}:

buildGoModule (finalAttrs: {
  pname = "wtp";
  version = "2.10.3";

  src = fetchFromGitHub {
    owner = "satococoa";
    repo = "wtp";
    rev = "v${finalAttrs.version}";
    hash = "sha256-KgayKjH4iHi7LgWwk2Laba33bMVZdbiMQgSmqBSTfZ0=";
  };

  vendorHash = "sha256-zsSNo1MQgpvH3ZSd3kmvdIpOCVJgSu1/pYLltx/9dZg=";

  subPackages = [ "cmd/wtp" ];

  ldflags = [
    "-s"
    "-w"
    "-X main.version=${finalAttrs.version}"
  ];

  env = {
    CGO_ENABLED = 0;
  };

  doCheck = false;

  nativeBuildInputs = [ installShellFiles ];

  postInstall = ''
    installShellCompletion --cmd wtp \
      --bash <($out/bin/wtp completion bash) \
      --fish <($out/bin/wtp completion fish) \
      --zsh <($out/bin/wtp completion zsh)
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Worktree Plus - Enhanced worktree management with automated setup and hooks";
    homepage = "https://github.com/satococoa/wtp";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = "wtp";
    platforms = lib.platforms.unix;
  };
})
