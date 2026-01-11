{
  lib,
  fetchzip,
  versionCheckHook,
  stdenvNoCC,
  installShellFiles,
  autoPatchelfHook,
  fd,
  ripgrep,
  makeWrapper,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "pi-coding-agent";
  version = "0.42.5";

  src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

  nativeBuildInputs = [ makeWrapper ];

  installPhase = ''
    runHook preInstall
    mkdir -p $out/lib/pi-coding-agent $out/bin
    cp -r . $out/lib/pi-coding-agent
    ln -s $out/lib/pi-coding-agent/pi $out/bin/pi
    runHook postInstall
  '';

  postInstall = ''
    wrapProgram $out/bin/pi \
      --suffix PATH : ${
        lib.makeBinPath [
          fd
          ripgrep
        ]
      }
  '';

  doInstallCheck = true;
  nativeInstallCheckInputs = [ versionCheckHook ];
  versionCheckProgram = "${placeholder "out"}/bin/pi";

  passthru = {
    sources = {
      aarch64-darwin = fetchzip {
        url = "https://github.com/badlogic/pi-mono/releases/download/v${finalAttrs.version}/pi-darwin-arm64.tar.gz";
        stripRoot = false;
        hash = "sha256-GGP7/JHuda6c/V9vDC3Ed572PkvyVunk+AXkahPqAZ4=";
      };
      x86_64-darwin = fetchzip {
        url = "https://github.com/badlogic/pi-mono/releases/download/v${finalAttrs.version}/pi-darwin-x64.tar.gz";
        stripRoot = false;
        hash = "sha256-mOJn4mW5AVQudXs7EMSPtpKcBKNzX8NlkA3EW+vN9ZQ=";
      };
      aarch64-linux = fetchzip {
        url = "https://github.com/badlogic/pi-mono/releases/download/v${finalAttrs.version}/pi-linux-arm64.tar.gz";
        stripRoot = false;
        hash = "sha256-qqs0GLXQT1ZQqWJyyJ5oMc697Efn2V2Ph38BUdYB7m0=";
      };
      x86_64-linux = fetchzip {
        url = "https://github.com/badlogic/pi-mono/releases/download/v${finalAttrs.version}/pi-linux-x64.tar.gz";
        stripRoot = false;
        hash = "sha256-MPJzAF1SJd6dCgXB3Hm0NjlU8QCjehx31R7FMQk7oLA=";
      };
    };
    updateScript = ./update.sh;
  };

  meta = {
    description = "Coding agent CLI with read, bash, edit, write tools and session management";
    homepage = "https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = builtins.attrNames finalAttrs.passthru.sources;
    mainProgram = "pi";
  };
})
