{
  fetchFromGitHub,
  fetchurl,
  lib,
  makeBinaryWrapper,
  nodejs_24,
  pnpm_10,
  stdenvNoCC,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "sentry";
  version = "0.45.0";
  sentryClientId = "1d673b81d60ef84c951359c36296972ca6fd41bd8f45acd2d3a783a3b3c28e41";

  src = fetchFromGitHub {
    owner = "getsentry";
    repo = "cli";
    tag = finalAttrs.version;
    hash = "sha256-Mep49YdEB3Wx3AbVDJL/j3RmElzc6ofrj++Fq+foa3k=";
  };

  # @sentry/api version pinned in pnpm-lock.yaml; determines the OpenAPI spec tag
  sentryApiVersion = "0.256.0";

  openapi_spec = fetchurl {
    url = "https://raw.githubusercontent.com/getsentry/sentry-api-schema/${finalAttrs.sentryApiVersion}/openapi-derefed.json";
    hash = "sha256-O+nVUIfXVEvqTDNSSdAVONHpqlrA1VaTDf0Q/kLBQI8=";
  };

  # Hoist workspace dependencies and fetch binaries for supported platforms
  patches = [ ./pnpm-workspace.patch ];

  pnpmDeps = pnpm_10.fetchDeps {
    inherit (finalAttrs)
      pname
      version
      src
      patches
      ;
    fetcherVersion = 4;
    hash = "sha256-E8l5V/As0m9IzL6A1YKv5l8C1i+08yIEvMxew7k2rr8=";
  };

  nativeBuildInputs = [
    makeBinaryWrapper
    nodejs_24
    pnpm_10.configHook
    pnpm_10
  ];

  postPatch = ''
    # Prevent schema fetch by replacing the OpenAPI spec with nix derivation
    substituteInPlace packages/cli/script/generate-api-schema.ts \
      --replace-fail \
        'await fetch(openApiUrl)' \
        'await (async () => ({ ok: true, json: async () => JSON.parse(require("fs").readFileSync("${finalAttrs.openapi_spec}", "utf-8")) }))()'
  '';

  buildPhase = ''
    runHook preBuild

    export SENTRY_CLIENT_ID="${finalAttrs.sentryClientId}"

    pnpm run bundle

    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall

    mkdir -p $out/{bin,lib/sentry}
    cp -R packages/cli/dist/. $out/lib/sentry/

    makeWrapper ${lib.getExe nodejs_24} $out/bin/sentry \
      --add-flags "$out/lib/sentry/bin.cjs"

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
