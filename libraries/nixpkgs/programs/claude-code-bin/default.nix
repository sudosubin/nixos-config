{
  autoPatchelfHook,
  fetchurl,
  lib,
  makeWrapper,
  stdenvNoCC,
  versionCheckHook,
  writableTmpDirAsHomeHook,
  zlib,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "claude-code-bin";
  version = "2.1.52";

  src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

  nativeBuildInputs = [
    makeWrapper
  ]
  ++ lib.optionals stdenvNoCC.hostPlatform.isLinux [ autoPatchelfHook ];

  buildInputs = lib.optionals stdenvNoCC.hostPlatform.isLinux [
    stdenvNoCC.cc.cc.lib
    zlib
  ];

  dontUnpack = true;

  installPhase = ''
    runHook preInstall
    install -Dm755 $src $out/bin/claude
    runHook postInstall
  '';

  env.AUTHORIZED = "1";

  # `claude-code` tries to auto-update by default, this disables that functionality.
  # https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview#environment-variables
  # The DEV=true env var causes claude to crash with `TypeError: window.WebSocket is not a constructor`
  postFixup = ''
    wrapProgram $out/bin/claude \
      --set DISABLE_AUTOUPDATER 1 \
      --unset DEV
  '';

  dontStrip = true;

  doInstallCheck = true;

  nativeInstallCheckInputs = [
    writableTmpDirAsHomeHook
    versionCheckHook
  ];

  passthru = {
    sources = {
      x86_64-linux = fetchurl {
        url = "https://storage.googleapis.com/claude-code-dist-86c565f3-f756-42ad-8dfa-d59b1c096819/claude-code-releases/${finalAttrs.version}/linux-x64/claude";
        hash = "sha256-cMH5iBt8CRxJ82lclMOB2cygrwlLy8mcufRj5E2Xzpw=";
      };
      aarch64-linux = fetchurl {
        url = "https://storage.googleapis.com/claude-code-dist-86c565f3-f756-42ad-8dfa-d59b1c096819/claude-code-releases/${finalAttrs.version}/linux-arm64/claude";
        hash = "sha256-r+CBmQk2VQqY7caAhg5vFs2frTAPtTtKsnxwcccJaPI=";
      };
      x86_64-darwin = fetchurl {
        url = "https://storage.googleapis.com/claude-code-dist-86c565f3-f756-42ad-8dfa-d59b1c096819/claude-code-releases/${finalAttrs.version}/darwin-x64/claude";
        hash = "sha256-RHpvoyOKpwB7/8xZkQTcQ43mHQyA/6rELR1Ojrbrl8A=";
      };
      aarch64-darwin = fetchurl {
        url = "https://storage.googleapis.com/claude-code-dist-86c565f3-f756-42ad-8dfa-d59b1c096819/claude-code-releases/${finalAttrs.version}/darwin-arm64/claude";
        hash = "sha256-IejEmzER+mnoj0UKlO5OiN9pMSgjAXu/Yf+GpGH8/CM=";
      };
    };
    updateScript = ./update.sh;
  };

  meta = {
    description = "Agentic coding tool that lives in your terminal, understands your codebase, and helps you code faster";
    homepage = "https://claude.ai/code";
    downloadPage = "https://github.com/anthropics/claude-code/releases";
    changelog = "https://github.com/anthropics/claude-code/releases";
    license = lib.licenses.unfree;
    sourceProvenance = with lib.sourceTypes; [ binaryNativeCode ];
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = "claude";
    platforms = builtins.attrNames finalAttrs.passthru.sources;
  };
})
