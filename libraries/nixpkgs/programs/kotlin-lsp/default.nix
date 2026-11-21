{
  autoPatchelfHook,
  fetchzip,
  fontconfig,
  freetype,
  lib,
  stdenv,
  stdenvNoCC,
  zlib,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "kotlin-lsp";
  version = "271.2085.0";

  src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

  nativeBuildInputs = lib.optionals stdenvNoCC.hostPlatform.isLinux [
    autoPatchelfHook
  ];

  buildInputs = lib.optionals stdenvNoCC.hostPlatform.isLinux [
    stdenv.cc.cc.lib
    fontconfig
    freetype
    zlib
  ];

  installPhase = ''
    runHook preInstall

    mkdir -p $out/bin $out/lib/kotlin-lsp
    cp -r * $out/lib/kotlin-lsp
    ${
      if stdenvNoCC.hostPlatform.isDarwin then
        "chmod +x $out/lib/kotlin-lsp/jbr/Contents/Home/bin/java"
      else if stdenvNoCC.hostPlatform.isLinux then
        "chmod +x $out/lib/kotlin-lsp/jbr/bin/java"
      else
        "echo 'Unsupported Platform' && exit 1"
    }
    chmod +x $out/lib/kotlin-lsp/bin/intellij-server
    ln -s $out/lib/kotlin-lsp/bin/intellij-server $out/bin/kotlin-lsp

    runHook postInstall
  '';

  passthru = {
    sources = {
      x86_64-linux = fetchzip {
        url = "https://download.jetbrains.com/language-server/kotlin-server/${finalAttrs.version}/kotlin-server-${finalAttrs.version}.tar.gz";
        hash = "sha256-lB+KkyW8h0j4Xpi//+IVxJvdSu2XFRS2QOwGHfrRG58=";
      };
      aarch64-linux = fetchzip {
        url = "https://download.jetbrains.com/language-server/kotlin-server/${finalAttrs.version}/kotlin-server-${finalAttrs.version}-aarch64.tar.gz";
        hash = "sha256-gGQ1WrTurM9uE3RmzabCAHiTLTEgUVO3hgvH5ft9IXM=";
      };
      aarch64-darwin = fetchzip {
        url = "https://download.jetbrains.com/language-server/kotlin-server/${finalAttrs.version}/kotlin-server-${finalAttrs.version}-aarch64.sit";
        extension = "zip";
        hash = "sha256-33Jos2E3fi8rxqEbZuJ6t3LnPZEIEFgNUq4VLHT5yjk=";
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
