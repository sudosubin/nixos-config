{
  fetchFromGitHub,
  lib,
  nix-update-script,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "pi-review.ts";
  version = "1.1.1";

  src = fetchFromGitHub {
    owner = "mitsuhiko";
    repo = "agent-stuff";
    rev = finalAttrs.version;
    hash = "sha256-4j+lYV/ZrlUTlvFHfO6i+3hvxVBLhbeoRaxM+UJpt+Q=";
  };

  dontBuild = true;

  installPhase = ''
    runHook preInstall
    install -Dm644 pi-extensions/review.ts $out
    runHook postInstall
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Code Review Extension (inspired by Codex's review feature)";
    homepage = "https://github.com/mitsuhiko/agent-stuff";
    license = lib.licenses.asl20;
    maintainers = with lib.maintainers; [ sudosubin ];
  };
})
