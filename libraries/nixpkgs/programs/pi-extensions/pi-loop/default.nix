{
  fetchFromGitHub,
  lib,
  nix-update-script,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "pi-loop.ts";
  version = "1.6.0-unstable-2026-04-22";

  src = fetchFromGitHub {
    owner = "mitsuhiko";
    repo = "agent-stuff";
    rev = "620e40df1a8baf1fddf98c2936bdccef8d0f589a";
    hash = "sha256-+K6QghYdXS5a3CN4+TNB7oY2XW+Y1L4w0GL+ziqezek=";
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
