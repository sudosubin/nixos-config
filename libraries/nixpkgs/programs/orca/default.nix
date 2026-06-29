{
  fetchzip,
  lib,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "orca";
  version = "1.4.104";

  src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

  # The bundled `orca` CLI is a `#!/usr/bin/env bash` script; patching its
  # shebang would modify a file inside the signed .app bundle and invalidate
  # its code signature. Leave the bundle untouched so it stays launchable.
  dontPatchShebangs = true;

  installPhase = ''
    runHook preInstall

    mkdir -p "$out/Applications/Orca.app" "$out/bin"
    cp -R . "$out/Applications/Orca.app"
    ln -s "$out/Applications/Orca.app/Contents/Resources/bin/orca" "$out/bin/orca"

    runHook postInstall
  '';

  passthru = {
    sources = {
      aarch64-darwin = fetchzip {
        url = "https://github.com/stablyai/orca/releases/download/v${finalAttrs.version}/Orca-${finalAttrs.version}-arm64-mac.zip";
        hash = "sha256-KvOWd7oxsM7hQUjpN9VULJqynjEyJaqx8C8U2AZKmKo=";
      };
      x86_64-darwin = fetchzip {
        url = "https://github.com/stablyai/orca/releases/download/v${finalAttrs.version}/Orca-${finalAttrs.version}-mac.zip";
        hash = "sha256-UwoC1/u3Z1vK8l+P/1ANfM1fO/baQvYAEGy1fy9OCGc=";
      };
    };
    updateScript = ./update.sh;
  };

  meta = {
    description = "IDE for orchestrating AI coding agents across terminals and worktrees";
    homepage = "https://www.onorca.dev/";
    changelog = "https://github.com/stablyai/orca/releases/tag/v${finalAttrs.version}";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = "orca";
    platforms = builtins.attrNames finalAttrs.passthru.sources;
  };
})
