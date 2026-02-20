{
  fetchFromGitHub,
  lib,
  nix-update-script,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "pi-interactive-shell.ts";
  version = "0.54.0";

  src = fetchFromGitHub {
    owner = "badlogic";
    repo = "pi-mono";
    rev = "v${finalAttrs.version}";
    hash = "sha256-j8h8KKt/1m47Y6/KA8g213gooq0n2fAqBVkKhHsBCGw=";
  };

  dontBuild = true;

  installPhase = ''
    runHook preInstall
    install -Dm644 packages/coding-agent/examples/extensions/interactive-shell.ts $out
    runHook postInstall
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Interactive shell commands extension for pi";
    homepage = "https://github.com/badlogic/pi-mono";
    license = lib.licenses.asl20;
    maintainers = with lib.maintainers; [ sudosubin ];
  };
})
