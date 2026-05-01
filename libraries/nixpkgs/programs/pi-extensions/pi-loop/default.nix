{
  fetchFromGitHub,
  lib,
  nix-update-script,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "pi-loop.ts";
  version = "1.6.0-unstable-2026-04-29";

  src = fetchFromGitHub {
    owner = "mitsuhiko";
    repo = "agent-stuff";
    rev = "b861028c706edf3e3f983cde09dd8cc8549ec948";
    hash = "sha256-jsAYm7CgXw6+ZeB/0ZCzsKUu/zNk8FLqU/TR2ZTjEtw=";
  };

  dontBuild = true;

  installPhase = ''
    runHook preInstall
    install -Dm644 extensions/loop.ts $out
    runHook postInstall
  '';

  passthru.updateScript = nix-update-script {
    extraArgs = [ "--version=branch" ];
  };

  meta = {
    description = "Loop extension for pi with breakout conditions";
    homepage = "https://github.com/mitsuhiko/agent-stuff";
    license = lib.licenses.asl20;
    maintainers = with lib.maintainers; [ sudosubin ];
  };
})
