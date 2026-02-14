{
  fetchFromGitHub,
  fetchPnpmDeps,
  lib,
  makeBinaryWrapper,
  nix-update-script,
  nodejs_24,
  pnpm_10,
  pnpmConfigHook,
  rustPlatform,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "agent-browser";
  version = "0.10.0";

  src = fetchFromGitHub {
    owner = "vercel-labs";
    repo = "agent-browser";
    tag = "v${finalAttrs.version}";
    hash = "sha256-Xn11Ja58atexoFZVdpo6OPW3PsuKB5P3DuA5EMSbROg=";
  };

  dontUnpack = true;

  nativeBuildInputs = [ makeBinaryWrapper ];

  installPhase = ''
    runHook preInstall

    mkdir -p $out/{bin,lib/agent-browser}
    ln -s ${finalAttrs.passthru.daemon}/{dist,node_modules,package.json} $out/lib/agent-browser/

    makeBinaryWrapper ${lib.getExe finalAttrs.passthru.cli} $out/bin/agent-browser \
      --set AGENT_BROWSER_HOME $out/lib/agent-browser \
      --prefix PATH : ${lib.makeBinPath [ nodejs_24 ]}

    runHook postInstall
  '';

  passthru = {
    cli = rustPlatform.buildRustPackage {
      pname = "${finalAttrs.pname}-cli";
      inherit (finalAttrs) version src;

      sourceRoot = "${finalAttrs.src.name}/cli";

      cargoHash = "sha256-k+ZrEBaaqRt8QT5k+7/Vp17AmcOvDkD87eb1LE00PNo=";

      meta = {
        mainProgram = "agent-browser";
        platforms = lib.platforms.unix;
      };
    };

    daemon = stdenvNoCC.mkDerivation {
      pname = "${finalAttrs.pname}-daemon";
      inherit (finalAttrs) version src;

      nativeBuildInputs = [
        nodejs_24
        pnpm_10
        pnpmConfigHook
      ];

      pnpmDeps = fetchPnpmDeps {
        inherit (finalAttrs) pname version src;
        fetcherVersion = 2;
        hash = "sha256-hBX/ao4QKildvKxTDFSYAhvxrupyltKCJUzvKnHukpc=";
      };

      postPatch = ''
        substituteInPlace package.json \
          --replace-fail '"postinstall": "node scripts/postinstall.js",' "" \
          --replace-fail '"prepare": "husky",' ""
      '';

      buildPhase = ''
        runHook preBuild
        pnpm run build
        runHook postBuild
      '';

      installPhase = ''
        runHook preInstall
        mkdir -p $out
        cp -r dist node_modules package.json $out/
        runHook postInstall
      '';
    };

    updateScript = nix-update-script {
      extraArgs = [
        "--subpackage"
        "cli"
        "--subpackage"
        "daemon"
      ];
    };
  };

  meta = {
    description = "Headless browser automation CLI for AI agents";
    homepage = "https://github.com/vercel-labs/agent-browser";
    changelog = "https://github.com/vercel-labs/agent-browser/blob/main/CHANGELOG.md";
    license = lib.licenses.asl20;
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = "agent-browser";
    platforms = lib.platforms.unix;
  };
})
