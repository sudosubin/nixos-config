{
  bun,
  fetchFromGitHub,
  lib,
  nix-update-script,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "agent-slack";
  version = "0.9.1";

  src = fetchFromGitHub {
    owner = "stablyai";
    repo = "agent-slack";
    tag = "v${finalAttrs.version}";
    hash = "sha256-+uMwZ2XWZioG2OACEazBX8ARoFSezSQehXDFOzo6J+I=";
  };

  bunDeps = stdenvNoCC.mkDerivation {
    name = "agent-slack-bun-deps";
    inherit (finalAttrs) src;

    nativeBuildInputs = [ bun ];

    buildPhase = ''
      export HOME=$(mktemp -d)
      bun install --frozen-lockfile --ignore-scripts
    '';

    installPhase = ''
      cp -r node_modules $out
    '';

    outputHash = "sha256-JU/joVXY5FNE6ffkZXDlYNoTNboHiYVOaDR/0OxUKVo=";
    outputHashAlgo = "sha256";
    outputHashMode = "recursive";
  };

  nativeBuildInputs = [ bun ];

  buildPhase = ''
    runHook preBuild

    cp -r ${finalAttrs.bunDeps} node_modules
    chmod -R +w node_modules

    export HOME=$(mktemp -d)
    bun build src/index.ts \
      --compile \
      --outfile=agent-slack \
      --define "AGENT_SLACK_BUILD_VERSION='${finalAttrs.version}'"

    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall

    install -Dm755 agent-slack $out/bin/agent-slack

    runHook postInstall
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Slack automation CLI for AI agents";
    homepage = "https://github.com/stablyai/agent-slack";
    changelog = "https://github.com/stablyai/agent-slack/releases/tag/v${finalAttrs.version}";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = "agent-slack";
    platforms = lib.platforms.unix;
  };
})
