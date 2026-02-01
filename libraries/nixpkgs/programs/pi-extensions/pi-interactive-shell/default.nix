{
  fetchFromGitHub,
  lib,
  nix-update-script,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "pi-interactive-shell.ts";
  version = "0.50.9";

  src = fetchFromGitHub {
    owner = "badlogic";
    repo = "pi-mono";
    rev = "v${finalAttrs.version}";
    hash = "sha256-LffWkdGCpFEDOO1QtZek7n/3BYv6L92vf4Uw9/JBs38=";
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
