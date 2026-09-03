{
  autoPatchelfHook,
  fetchzip,
  installShellFiles,
  lib,
  stdenvNoCC,
  versionCheckHook,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "linear-cli";
  version = "2.6.0";

  src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

  nativeBuildInputs = [
    installShellFiles
  ]
  ++ lib.optional stdenvNoCC.hostPlatform.isLinux autoPatchelfHook;

  installPhase = ''
    runHook preInstall
    install -Dm755 linear $out/bin/linear
    runHook postInstall
  '';

  postInstall = ''
    installShellCompletion --cmd linear \
      --bash <($out/bin/linear completions bash) \
      --fish <($out/bin/linear completions fish) \
      --zsh <($out/bin/linear completions zsh)
  '';

  doInstallCheck = true;
  nativeInstallCheckInputs = [ versionCheckHook ];
  versionCheckProgram = "${placeholder "out"}/bin/linear";

  passthru = {
    sources = {
      aarch64-darwin = fetchzip {
        url = "https://github.com/schpet/linear-cli/releases/download/v${finalAttrs.version}/linear-aarch64-apple-darwin.tar.xz";
        hash = "sha256-uuxWxWjgsO89GggPXYjmw+1S+v2l29dkZt91mJ+Ghbo=";
      };
      aarch64-linux = fetchzip {
        url = "https://github.com/schpet/linear-cli/releases/download/v${finalAttrs.version}/linear-aarch64-unknown-linux-gnu.tar.xz";
        hash = "sha256-Dc8mIv1jpf58AAgx/RQnSwXtdxzSEj66oOytGvh2Fio=";
      };
      x86_64-linux = fetchzip {
        url = "https://github.com/schpet/linear-cli/releases/download/v${finalAttrs.version}/linear-x86_64-unknown-linux-gnu.tar.xz";
        hash = "sha256-i6U571U5w9+dSEkBbCZZ5aiXmfL2zjDyJBGUQQbV2dE=";
      };
    };
    updateScript = ./update.sh;
  };

  meta = {
    description = "CLI tool for linear.app that uses git branch names and directory names to open issues and team pages";
    homepage = "https://github.com/schpet/linear-cli";
    license = lib.licenses.isc;
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = "linear";
    platforms = builtins.attrNames finalAttrs.passthru.sources;
  };
})
