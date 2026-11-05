{
  buildNpmPackage,
  fetchFromGitHub,
  lib,
  nodejs_24,
}:

buildNpmPackage (finalAttrs: {
  pname = "material-icon-theme";
  version = "5.40.0";

  src = fetchFromGitHub {
    owner = "material-extensions";
    repo = "vscode-material-icon-theme";
    tag = "v${finalAttrs.version}";
    hash = "sha256-oKB54ewYX8tfr2nDx0fA3K6ALGF4TsK2Tbn1GpVRy5w=";
  };

  nodejs = nodejs_24;
  npmDepsHash = "sha256-un8BKw6DJjiqji9F/j+4GwyhUhO04oAravPdpyY7S6c=";

  # upstream's lockfile lacks resolved URLs for most packages (npm/cli#6301), so ship a regenerated one
  postPatch = ''
    cp ${./package-lock.json} package-lock.json
  '';

  env.PUPPETEER_SKIP_DOWNLOAD = "1";

  installPhase = ''
    runHook preInstall

    install -Dm644 dist/module/index.cjs -t $out/lib/node_modules/material-icon-theme/dist/module
    install -Dm644 package.json LICENSE -t $out/lib/node_modules/material-icon-theme
    cp -r icons $out/lib/node_modules/material-icon-theme/icons

    runHook postInstall
  '';

  passthru.updateScript = ./update.sh;

  meta = {
    description = "Material Design Icons for Visual Studio Code";
    homepage = "https://github.com/material-extensions/vscode-material-icon-theme/blob/main/README.md";
    changelog = "https://github.com/material-extensions/vscode-material-icon-theme/blob/v${finalAttrs.version}/CHANGELOG.md";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.all;
  };
})
