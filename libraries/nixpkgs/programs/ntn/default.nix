{
  autoPatchelfHook,
  fetchurl,
  lib,
  stdenvNoCC,
  versionCheckHook,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "ntn";
  version = "0.21.7";

  src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

  nativeBuildInputs = lib.optional stdenvNoCC.hostPlatform.isLinux autoPatchelfHook;

  installPhase = ''
    runHook preInstall
    install -Dm755 ntn $out/bin/ntn
    install -Dm644 README.md $out/share/doc/ntn/README.md
    install -Dm644 LICENSE.md $out/share/doc/ntn/LICENSE.md
    runHook postInstall
  '';

  doInstallCheck = true;
  nativeInstallCheckInputs = [ versionCheckHook ];
  versionCheckProgram = "${placeholder "out"}/bin/ntn";
  versionCheckProgramArg = "--version";

  passthru = {
    sources = {
      aarch64-darwin = fetchurl {
        url = "https://ntn.dev/releases/v${finalAttrs.version}/ntn-aarch64-apple-darwin.tar.gz";
        hash = "sha256-IVOA6L4k4bqMm+XSqJ6+0L1rrz4d4YdiJ9FAFzgt+Uc=";
      };
      aarch64-linux = fetchurl {
        url = "https://ntn.dev/releases/v${finalAttrs.version}/ntn-aarch64-unknown-linux-musl.tar.gz";
        hash = "sha256-7/bHKwgZNxVSRtfyqdCq3idV440y4EX6vzqI6vTHE2A=";
      };
      x86_64-linux = fetchurl {
        url = "https://ntn.dev/releases/v${finalAttrs.version}/ntn-x86_64-unknown-linux-musl.tar.gz";
        hash = "sha256-ZPfHLQqwyto1KqfPdSqBWhtpdpthI9ZVUCxlJsIlBzM=";
      };
    };
    updateScript = ./update.sh;
  };

  meta = {
    description = "Notion CLI for Workers and public API operations";
    homepage = "https://ntn.dev";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = "ntn";
    platforms = builtins.attrNames finalAttrs.passthru.sources;
  };
})
