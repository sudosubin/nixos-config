{
  fetchFromGitHub,
  fetchurl,
  cacert,
  lib,
  makeBinaryWrapper,
  nix-update-script,
  nodejs_24,
  pnpm_10,
  stdenvNoCC,
  writableTmpDirAsHomeHook,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "sentry";
  version = "0.38.0";
  sentryClientId = "1d673b81d60ef84c951359c36296972ca6fd41bd8f45acd2d3a783a3b3c28e41";

  src = fetchFromGitHub {
    owner = "getsentry";
    repo = "cli";
    tag = finalAttrs.version;
    hash = "sha256-RQCZzXAPMPZDB1mUoFpqA8P/7Gs4mkaf1KTHdB3HOwU=";
  };

  # @sentry/api version pinned in pnpm-lock.yaml; determines the OpenAPI spec tag
  sentryApiVersion = "0.180.0";

  openapi_spec = fetchurl {
    url = "https://raw.githubusercontent.com/getsentry/sentry-api-schema/${finalAttrs.sentryApiVersion}/openapi-derefed.json";
    hash = "sha256-wbY8nDUOeVrHi9wXzS+YowISvTXcKK9oa2bbZPMfVhU=";
  };

  node_modules = stdenvNoCC.mkDerivation {
    pname = "${finalAttrs.pname}-node_modules";
    inherit (finalAttrs) version src;

    impureEnvVars = lib.fetchers.proxyImpureEnvVars ++ [
      "GIT_PROXY_COMMAND"
      "SOCKS_SERVER"
    ];

    nativeBuildInputs = [
      cacert
      nodejs_24
      pnpm_10
      writableTmpDirAsHomeHook
    ];

    # nixpkgs' Node.js uses the system OpenSSL CA store, which is empty inside
    # the (fixed-output) build sandbox, so pnpm's TLS fetches to the npm
    # registry fail with UNABLE_TO_GET_ISSUER_CERT_LOCALLY. Point both Node
    # and OpenSSL at the cacert bundle. This only enables the network fetch;
    # the resolved package set stays lockfile-deterministic so the fixed
    # outputHash is unaffected.
    env = {
      NODE_EXTRA_CA_CERTS = "${cacert}/etc/ssl/certs/ca-bundle.crt";
      SSL_CERT_FILE = "${cacert}/etc/ssl/certs/ca-bundle.crt";
    };

    dontConfigure = true;

    # Add .npmrc, package.json, pnpm-workspace.yaml patches
    patches = [ ./pnpm-workspace.patch ];

    buildPhase = ''
      runHook preBuild
      pnpm install --frozen-lockfile
      # Prevent timestamp and absolute build paths recorded by pnpm
      rm -f node_modules/.modules.yaml node_modules/.pnpm-workspace-state-v1.json
      runHook postBuild
    '';

    installPhase = ''
      runHook preInstall
      mkdir -p $out
      cp -R node_modules $out/
      runHook postInstall
    '';

    dontFixup = true;

    outputHash = "sha256-u3vKGKuOYRYpbiYbbjeFpJD0m/NYzF+jRUQROfzKi/I=";
    outputHashAlgo = "sha256";
    outputHashMode = "recursive";
  };

  nativeBuildInputs = [
    makeBinaryWrapper
    nodejs_24
    pnpm_10
  ];

  # Add .npmrc, package.json, pnpm-workspace.yaml patches
  patches = [ ./pnpm-workspace.patch ];

  postPatch = ''
    # Prevent schema fetch by replacing the OpenAPI spec with nix derivation
    substituteInPlace script/generate-api-schema.ts \
      --replace-fail \
        'await fetch(openApiUrl)' \
        'await (async () => ({ ok: true, json: async () => JSON.parse(require("fs").readFileSync("${finalAttrs.openapi_spec}", "utf-8")) }))()'
  '';

  buildPhase = ''
    runHook preBuild

    export HOME=$TMPDIR
    export SENTRY_CLIENT_ID="${finalAttrs.sentryClientId}"

    cp -r ${finalAttrs.node_modules}/node_modules .
    chmod -R u+w node_modules

    pnpm run bundle

    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall

    mkdir -p $out/{bin,lib/sentry}
    cp dist/bin.cjs dist/index.cjs dist/ink-app.js $out/lib/sentry/

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
