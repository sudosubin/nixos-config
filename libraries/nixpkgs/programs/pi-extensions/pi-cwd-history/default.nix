{
  fetchFromGitHub,
  lib,
  nix-update-script,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "pi-cwd-history.ts";
  version = "1.3.0";

  src = fetchFromGitHub {
    owner = "mitsuhiko";
    repo = "agent-stuff";
    rev = "v${finalAttrs.version}";
    hash = "sha256-DoCpmgKJE8UUo0I4ueIyH3LM4RM6enF8KQ6r2y0qGH0=";
  };

  patches = [ ./respect-pi-coding-agent-dir.patch ];

  dontBuild = true;

  installPhase = ''
    runHook preInstall
    install -Dm644 pi-extensions/cwd-history.ts $out
    runHook postInstall
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Working directory history extension for pi";
    homepage = "https://github.com/mitsuhiko/agent-stuff";
    license = lib.licenses.asl20;
    maintainers = with lib.maintainers; [ sudosubin ];
  };
})
