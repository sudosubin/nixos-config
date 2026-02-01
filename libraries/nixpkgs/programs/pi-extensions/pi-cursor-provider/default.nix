{
  buildNpmPackage,
  fetchFromGitHub,
  lib,
  nix-update-script,
}:

buildNpmPackage (finalAttrs: {
  pname = "pi-cursor-provider";
  version = "0-unstable-2026-01-31";

  src = fetchFromGitHub {
    owner = "nicobailon";
    repo = "pi-cursor-provider";
    rev = "be6ecd80578a4573f7f406ea1a0b237f15e1bf28";
    hash = "sha256-q4mD4sYnEwlHBfSDJnd8RhvzFWqCxEoKSvjIWTxjiSg=";
  };

  npmDepsHash = "sha256-ULSGsD4cBPDk9PErDc069RYrWLUFs1WdGgBIuolPscM=";

  patches = [ ./respect-pi-coding-agent-dir.patch ];

  dontNpmBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p $out
    cp -r package.json src node_modules $out/
    runHook postInstall
  '';

  passthru.updateScript = nix-update-script {
    extraArgs = [ "--version=branch" ];
  };

  meta = {
    description = "Use Cursor's AI models inside Pi coding agent";
    homepage = "https://github.com/nicobailon/pi-cursor-provider";
    license = lib.licenses.unlicense;
    maintainers = with lib.maintainers; [ sudosubin ];
  };
})
