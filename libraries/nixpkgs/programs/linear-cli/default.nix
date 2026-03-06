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
  version = "1.11.0";

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
        hash = "sha256-ZyCPgH4F6ma7FKV6/iLhIq+ro9Awg6O2xInDflslZ2U=";
      };
      x86_64-darwin = fetchzip {
        url = "https://github.com/schpet/linear-cli/releases/download/v${finalAttrs.version}/linear-x86_64-apple-darwin.tar.xz";
        hash = "sha256-IewLvJlQAz5IvZBdt33Rs55KXABdDVDqR9A8bqmtReQ=";
      };
      aarch64-linux = fetchzip {
        url = "https://github.com/schpet/linear-cli/releases/download/v${finalAttrs.version}/linear-aarch64-unknown-linux-gnu.tar.xz";
        hash = "sha256-s6nYNfjJOv7/dGOguYJAAL76ugsb4G8U66wHlw2YjRo=";
      };
      x86_64-linux = fetchzip {
        url = "https://github.com/schpet/linear-cli/releases/download/v${finalAttrs.version}/linear-x86_64-unknown-linux-gnu.tar.xz";
        hash = "sha256-H+CETrGeYeDXYaRlIxnTBfIq2X8qKsU+rYGZqAJuUwY=";
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
