{
  buildNpmPackage,
  fetchFromGitHub,
  lib,
  makeWrapper,
  nix-update-script,
  nodejs_24,
  playwright-driver,
}:

buildNpmPackage (finalAttrs: {
  pname = "damn-my-slow-kt";
  version = "0.5.27";

  src = fetchFromGitHub {
    owner = "kargnas";
    repo = "damn-my-slow-kt";
    tag = "v${finalAttrs.version}";
    hash = "sha256-dz0CmSaGSwlGq0JYjcH3SNZ+8EBlkDAaki66POFiWjM=";
  };

  nodejs = nodejs_24;
  npmDepsHash = "sha256-l5JuyBneViNSMzyNkO0SaIIlElw43qCFaqSLnd53PCw=";

  nativeBuildInputs = [ makeWrapper ];

  env.PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = "1";

  npmBuildScript = "build";

  installPhase = ''
    runHook preInstall

    mkdir -p "$out/bin" "$out/libexec/${finalAttrs.pname}"
    cp -r bin dist node_modules package.json README.md "$out/libexec/${finalAttrs.pname}/"

    makeWrapper ${lib.getExe nodejs_24} "$out/bin/${finalAttrs.pname}" \
      --set PLAYWRIGHT_BROWSERS_PATH ${playwright-driver.browsers} \
      --inherit-argv0 \
      --add-flags "$out/libexec/${finalAttrs.pname}/bin/${finalAttrs.pname}"

    runHook postInstall
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "CLI tool for automating KT SLA speed tests and fee reduction claims";
    homepage = "https://github.com/kargnas/damn-my-slow-kt";
    changelog = "https://github.com/kargnas/damn-my-slow-kt/releases/tag/v${finalAttrs.version}";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = finalAttrs.pname;
    platforms = lib.platforms.unix;
  };
})
