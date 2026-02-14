{
  buildNpmPackage,
  fetchFromGitHub,
  lib,
  nix-update-script,
}:

buildNpmPackage (finalAttrs: {
  pname = "pi-cursor-agent";
  version = "0.1.3";

  src = fetchFromGitHub {
    owner = "sudosubin";
    repo = "pi-cursor-agent";
    tag = "v${finalAttrs.version}";
    hash = "sha256-fgusAx4g4pEZ8ukA7w54oVrozXdRQmh4HKUkGMC+76E=";
  };

  npmDepsHash = "sha256-DD1s5llQ56J/k6IdGz0WRzTPfanPlWs3F6L/gbJqlJE=";

  dontNpmBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p $out
    cp -r package.json src node_modules $out/
    runHook postInstall
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Cursor Agent provider extension for pi";
    homepage = "https://github.com/sudosubin/pi-cursor-agent";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
  };
})
