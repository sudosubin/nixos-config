{
  bun,
  fetchFromGitHub,
  fetchurl,
  lib,
  makeBinaryWrapper,
  nix-update-script,
  stdenvNoCC,
  writableTmpDirAsHomeHook,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "sentry";
  version = "0.34.0";
  sentryClientId = "1d673b81d60ef84c951359c36296972ca6fd41bd8f45acd2d3a783a3b3c28e41";

  src = fetchFromGitHub {
    owner = "getsentry";
    repo = "cli";
    tag = finalAttrs.version;
    hash = "sha256-OURZ6ZSv7PHkw+Yb/njp2b3Jf5EOfzTNG4zbS1iZ5mc=";
  };

  # @sentry/api version pinned in bun.lock; determines the OpenAPI spec tag
  sentryApiVersion = "0.141.0";

  openapi_spec = fetchurl {
    url = "https://raw.githubusercontent.com/getsentry/sentry-api-schema/${finalAttrs.sentryApiVersion}/openapi-derefed.json";
    hash = "sha256-GjGMWxTRVora4p2EwizEpvdcKbIbXHpn1/+fyKeCO+4=";
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

    outputHash = "sha256-XsixZfs4U5EuVEqyLNikkNSm54pEX4wQuOM2uny3Cgs=";
    outputHashAlgo = "sha256";
    outputHashMode = "recursive";
  };

  nativeBuildInputs = [
    bun
    makeBinaryWrapper
  ];

  buildPhase = ''
    runHook preBuild

    export HOME=$TMPDIR

    cp -r ${finalAttrs.node_modules}/node_modules .
    chmod -R u+w node_modules

    substituteInPlace script/generate-api-schema.ts \
      --replace-fail 'await fetch(openApiUrl)' \
        'await (async () => ({ ok: true, json: async () => JSON.parse(require("fs").readFileSync("${finalAttrs.openapi_spec}", "utf-8")) }))()'

    bun run generate:schema
    bun run generate:docs
    bun run generate:sdk

    bun build src/bin.ts \
      --outdir dist \
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
    cp -r dist/* $out/lib/sentry/

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
