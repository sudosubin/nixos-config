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
  version = "262.8190.0";

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

  # The bundled JetBrains Runtime ships AWT / splash-screen / sound native
  # libraries that link against desktop GUI stacks (X11, Wayland, ALSA). The
  # Kotlin language server runs headless (`intellij-server`) and never loads
  # them, so ignore these otherwise-unsatisfiable deps instead of dragging a
  # full desktop stack into the closure.
  autoPatchelfIgnoreMissingDeps = [
    "libX11.so.6"
    "libXext.so.6"
    "libXi.so.6"
    "libXrender.so.1"
    "libXtst.so.6"
    "libasound.so.2"
    "libwayland-client.so.0"
    "libwayland-cursor.so.0"
    "libxkbcommon.so.0"
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
        url = "https://download-cdn.jetbrains.com/language-server/kotlin-server/${finalAttrs.version}/kotlin-server-${finalAttrs.version}.tar.gz";
        hash = "sha256-/zOYoe+J1IZ1ZyNGOxfB/xObCHs55+e+9r7RbkbH/q8=";
      };
      aarch64-linux = fetchzip {
        url = "https://download-cdn.jetbrains.com/language-server/kotlin-server/${finalAttrs.version}/kotlin-server-${finalAttrs.version}-aarch64.tar.gz";
        hash = "sha256-SZ/Fjoe5fz8G7OBiTlRKwD8cVLrc674ptSYJ9T/XWic=";
      };
      x86_64-darwin = fetchzip {
        url = "https://download-cdn.jetbrains.com/language-server/kotlin-server/${finalAttrs.version}/kotlin-server-${finalAttrs.version}.sit";
        extension = "zip";
        hash = "sha256-e+6smD2MICLf0GiCAd1pQkVYjkrueofkDoHZihfMA0c=";
      };
      aarch64-darwin = fetchzip {
        url = "https://download-cdn.jetbrains.com/language-server/kotlin-server/${finalAttrs.version}/kotlin-server-${finalAttrs.version}-aarch64.sit";
        extension = "zip";
        hash = "sha256-3lR3rnjFtjC16NEW7NuMRgy/2ulqNsWo5iz9Eht8+B0=";
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
