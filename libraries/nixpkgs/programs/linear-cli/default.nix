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
  version = "2.0.0";

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
        hash = "sha256-g8ztuB+IBL+4SkhSGkOc8MTNubRV38mX+4I/ruVtdYQ=";
      };
      x86_64-darwin = fetchzip {
        url = "https://github.com/schpet/linear-cli/releases/download/v${finalAttrs.version}/linear-x86_64-apple-darwin.tar.xz";
        hash = "sha256-zHU3kDT4CPYo8h7SYOxkXGg7CLiUIzBN0xRqGzrl0n8=";
      };
      aarch64-linux = fetchzip {
        url = "https://github.com/schpet/linear-cli/releases/download/v${finalAttrs.version}/linear-aarch64-unknown-linux-gnu.tar.xz";
        hash = "sha256-uMqgs0IASfAwSRDA/tcTVidT/L7gaxn8aphnSttCFpQ=";
      };
      x86_64-linux = fetchzip {
        url = "https://github.com/schpet/linear-cli/releases/download/v${finalAttrs.version}/linear-x86_64-unknown-linux-gnu.tar.xz";
        hash = "sha256-/d3oOdKICbGk2zpCCTguSeSvSczJGFP7MiQfg9nr4aM=";
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
