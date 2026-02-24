{
  buildNpmPackage,
  fetchFromGitHub,
  lib,
  nix-update-script,
}:

buildNpmPackage (finalAttrs: {
  pname = "claude-agent-sdk-pi";
  version = "1.0.10-unstable-2026-02-13";

  src = fetchFromGitHub {
    owner = "prateekmedia";
    repo = "claude-agent-sdk-pi";
    rev = "b85bffb239e84d05d8cf8f13928432b7b25753db";
    hash = "sha256-wjVoOnqZm0dCNifyxNa2k6vXpby1tXSxAWuewYbh8g8=";
  };

  npmDepsHash = "sha256-MX8nXlde5N2Wrw6Iu0mUE1l9z8/ht1SNB4yU8CT9/28=";

  npmFlags = [ "--omit=peer" ];

  dontNpmBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p $out
    cp -r package.json index.ts node_modules $out/
    runHook postInstall
  '';

  passthru.updateScript = nix-update-script {
    extraArgs = [ "--version=branch" ];
  };

  meta = {
    description = "Claude agent SDK as a provider for pi";
    homepage = "https://github.com/prateekmedia/claude-agent-sdk-pi";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
  };
})
