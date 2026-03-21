{
  fetchzip,
  lib,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "kotlin-lsp";
  version = "262.2310.0";

  src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

  postPatch = ''
    substituteInPlace kotlin-lsp.sh \
      --replace-fail 'chmod +x "$LOCAL_JRE_PATH/bin/java"' '# chmod removed for nixpkgs'
  '';

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
        hash = "sha256-Bf2qkFpNhQC/Mz563OapmCXeKN+dTrYyQbOcF6z6b48=";
      };
      aarch64-linux = fetchzip {
        url = "https://download-cdn.jetbrains.com/kotlin-lsp/${finalAttrs.version}/kotlin-lsp-${finalAttrs.version}-linux-aarch64.zip";
        stripRoot = false;
        hash = "sha256-uyTVY4TX6YCv3/qow+CQeTRpez3PLegDX3OscpKPCUM=";
      };
      x86_64-darwin = fetchzip {
        url = "https://download-cdn.jetbrains.com/kotlin-lsp/${finalAttrs.version}/kotlin-lsp-${finalAttrs.version}-mac-x64.zip";
        stripRoot = false;
        hash = "sha256-VoDpfxzLBCvZcJlHmC0yp174s4Urc+cEGw0YA4ctRdE=";
      };
      aarch64-darwin = fetchzip {
        url = "https://download-cdn.jetbrains.com/kotlin-lsp/${finalAttrs.version}/kotlin-lsp-${finalAttrs.version}-mac-aarch64.zip";
        stripRoot = false;
        hash = "sha256-d9jImEUN4Np6PY7uczB5hIE89bq9O+hV+Ww1F8WLe68=";
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
