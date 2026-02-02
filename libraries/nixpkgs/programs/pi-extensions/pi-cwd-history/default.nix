{
  fetchFromGitHub,
  lib,
  nix-update-script,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "pi-cwd-history.ts";
  version = "1.2.0";

  src = fetchFromGitHub {
    owner = "mitsuhiko";
    repo = "agent-stuff";
    rev = "v${finalAttrs.version}";
    hash = "sha256-0amfYCRdvpm1ufJaEwgFTu1MPUIAdd0wM0xm22/V2H0=";
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
