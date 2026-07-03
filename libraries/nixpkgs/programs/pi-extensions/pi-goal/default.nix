{
  fetchFromGitHub,
  lib,
  nix-update-script,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "pi-goal.ts";
  version = "1.6.0-unstable-2026-06-21";

  src = fetchFromGitHub {
    owner = "mitsuhiko";
    repo = "agent-stuff";
    rev = "f1c881db21a9ec53977ff8379b74e64e290fef93";
    hash = "sha256-NCeQlZ1IPVB5O+Zkh24mqIpgKI92aION6R0IXoceKpM=";
  };

  dontBuild = true;

  installPhase = ''
    runHook preInstall
    install -Dm644 extensions/goal.ts $out
    runHook postInstall
  '';

  passthru.updateScript = nix-update-script {
    extraArgs = [ "--version=branch" ];
  };

  meta = {
    description = "Session-log-backed long-running objective mode for pi";
    homepage = "https://github.com/mitsuhiko/agent-stuff";
    license = lib.licenses.asl20;
    maintainers = with lib.maintainers; [ sudosubin ];
  };
})
