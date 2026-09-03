{
  fetchFromGitHub,
  lib,
  nix-update-script,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "pi-review.ts";
  version = "1.6.0-unstable-2026-08-30";

  src = fetchFromGitHub {
    owner = "mitsuhiko";
    repo = "agent-stuff";
    rev = "3c891a9640f80c271ccc666ab7a39f9811bc3fb6";
    hash = "sha256-k5YTyolAnND5J3L3q/1bHNMOKw0mv+G32WbxzgKm1HE=";
  };

  dontBuild = true;

  installPhase = ''
    runHook preInstall
    install -Dm644 extensions/review.ts $out
    runHook postInstall
  '';

  passthru.updateScript = nix-update-script {
    extraArgs = [ "--version=branch" ];
  };

  meta = {
    description = "Code Review Extension (inspired by Codex's review feature)";
    homepage = "https://github.com/mitsuhiko/agent-stuff";
    license = lib.licenses.asl20;
    maintainers = with lib.maintainers; [ sudosubin ];
  };
})
