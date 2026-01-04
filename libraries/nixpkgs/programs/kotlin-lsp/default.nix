{
  lib,
  stdenvNoCC,
  fetchzip,
  curl,
  jq,
  runCommand,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "kotlin-lsp";
  version = "261.13587.0";

  src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

  installPhase = ''
    runHook preInstall

    mkdir -p $out/bin $out/lib/kotlin-lsp
    cp -r * $out/lib/kotlin-lsp
    ${
      if stdenvNoCC.hostPlatform.isDarwin then
        "chmod +x $out/lib/kotlin-lsp/jre/Contents/Home/bin/java"
      else if stdenvNoCC.hostPlatform.isLinux then
        "chmod +x $out/lib/kotlin-lsp/jre/bin/java"
      else
        "echo 'Unsupported Platform' && exit 1"
    }
    chmod +x $out/lib/kotlin-lsp/kotlin-lsp.sh
    ln -s $out/lib/kotlin-lsp/kotlin-lsp.sh $out/bin/kotlin-lsp

    runHook postInstall
  '';

  passthru = {
    sources = {
      x86_64-linux = fetchzip {
        url = "https://download-cdn.jetbrains.com/kotlin-lsp/${finalAttrs.version}/kotlin-lsp-${finalAttrs.version}-linux-x64.zip";
        stripRoot = false;
        hash = "sha256-EweSqy30NJuxvlJup78O+e+JOkzvUdb6DshqAy1j9jE=";
      };
      aarch64-linux = fetchzip {
        url = "https://download-cdn.jetbrains.com/kotlin-lsp/${finalAttrs.version}/kotlin-lsp-${finalAttrs.version}-linux-aarch64.zip";
        stripRoot = false;
        hash = "sha256-MhHEYHBctaDH9JVkN/guDCG1if9Bip1aP3n+JkvHCvA=";
      };
      x86_64-darwin = fetchzip {
        url = "https://download-cdn.jetbrains.com/kotlin-lsp/${finalAttrs.version}/kotlin-lsp-${finalAttrs.version}-mac-x64.zip";
        stripRoot = false;
        hash = "sha256-zMuUcahT1IiCT1NTrMCIzUNM0U6U3zaBkJtbGrzF7I8=";
      };
      aarch64-darwin = fetchzip {
        url = "https://download-cdn.jetbrains.com/kotlin-lsp/${finalAttrs.version}/kotlin-lsp-${finalAttrs.version}-mac-aarch64.zip";
        stripRoot = false;
        hash = "sha256-zwlzVt3KYN0OXKr6sI9XSijXSbTImomSTGRGa+3zCK8=";
      };
    };
    updateScript = ./update.sh;
  };

  meta = {
    description = "Kotlin Language Server and plugin for Visual Studio Code";
    homepage = "https://github.com/Kotlin/kotlin-lsp";
    license = lib.licenses.asl20;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = builtins.attrNames finalAttrs.passthru.sources;
    mainProgram = "kotlin-lsp";
  };
})
