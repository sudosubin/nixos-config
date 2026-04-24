{
  bun,
  fetchFromGitHub,
  lib,
  makeBinaryWrapper,
  nix-update-script,
  stdenvNoCC,
  writableTmpDirAsHomeHook,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "sentry";
  version = "0.29.1";
  sentryClientId = "1d673b81d60ef84c951359c36296972ca6fd41bd8f45acd2d3a783a3b3c28e41";

  src = fetchFromGitHub {
    owner = "getsentry";
    repo = "cli";
    tag = finalAttrs.version;
    hash = "sha256-8hMSOw2FXBLw5zPySZbWJLGRBP/uOtctJA/jxPCPYyQ=";
  };

  api_schema = stdenvNoCC.mkDerivation {
    pname = "${finalAttrs.pname}-api-schema";
    inherit (finalAttrs) version src;

    impureEnvVars = lib.fetchers.proxyImpureEnvVars ++ [
      "GIT_PROXY_COMMAND"
      "SOCKS_SERVER"
    ];

    nativeBuildInputs = [
      bun
      writableTmpDirAsHomeHook
    ];

    dontConfigure = true;

    buildPhase = ''
      runHook preBuild
      cp -r ${finalAttrs.node_modules}/node_modules .
      bun run script/generate-api-schema.ts
      runHook postBuild
    '';

    installPhase = ''
      runHook preInstall
      mkdir -p $out
      cp src/generated/api-schema.json $out/
      runHook postInstall
    '';

    dontFixup = true;

    outputHash = "sha256-l+2iJBiohqWXEbprQ5nJvWi+ck0Jtk/p46IbclB/WJw=";
    outputHashAlgo = "sha256";
    outputHashMode = "recursive";
  };

  node_modules = stdenvNoCC.mkDerivation {
    pname = "${finalAttrs.pname}-node_modules";
    inherit (finalAttrs) version src;

    impureEnvVars = lib.fetchers.proxyImpureEnvVars ++ [
      "GIT_PROXY_COMMAND"
      "SOCKS_SERVER"
    ];

    nativeBuildInputs = [
      bun
      writableTmpDirAsHomeHook
    ];

    dontConfigure = true;

    buildPhase = ''
      runHook preBuild
      export BUN_INSTALL_CACHE_DIR=$(mktemp -d)
      bun install --frozen-lockfile --no-progress
      runHook postBuild
    '';

    installPhase = ''
      runHook preInstall
      mkdir -p $out
      cp -R node_modules $out/
      runHook postInstall
    '';

    dontFixup = true;

    outputHash = "sha256-jyS7h3VCSb0ygu9LIpdeJxKPfC5NixsNzoHCeb0Sldc=";
    outputHashAlgo = "sha256";
    outputHashMode = "recursive";
  };

  nativeBuildInputs = [
    bun
    makeBinaryWrapper
  ];

  buildPhase = ''
    runHook preBuild

    cp -r ${finalAttrs.node_modules}/node_modules .
    mkdir -p src/generated
    cp ${finalAttrs.api_schema}/api-schema.json src/generated/

    bun run generate:docs
    bun run generate:sdk

    bun build src/bin.ts \
      --outfile dist/bin.js \
      --target bun \
      --minify \
      --define 'SENTRY_CLI_VERSION="${finalAttrs.version}"' \
      --define 'SENTRY_CLIENT_ID_BUILD="${finalAttrs.sentryClientId}"' \
      --define 'process.env.NODE_ENV="production"'

    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall

    mkdir -p $out/{bin,lib/sentry}
    cp dist/bin.js $out/lib/sentry/

    makeWrapper ${lib.getExe bun} $out/bin/sentry \
      --add-flags "$out/lib/sentry/bin.js"

    runHook postInstall
  '';

  passthru.updateScript = ./update.sh;

  meta = {
    description = "Sentry CLI";
    homepage = "https://github.com/getsentry/cli";
    changelog = "https://github.com/getsentry/cli/releases/tag/${finalAttrs.version}";
    license = lib.licenses.fsl11Asl20;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.unix;
    mainProgram = "sentry";
  };
})
