{
  buildNpmPackage,
  fetchFromGitHub,
  lib,
  nodejs_24,
}:

buildNpmPackage (finalAttrs: {
  pname = "material-icon-theme";
  version = "5.39.0";

  src = fetchFromGitHub {
    owner = "material-extensions";
    repo = "vscode-material-icon-theme";
    tag = "v${finalAttrs.version}";
    hash = "sha256-rM0aMKLBw9sHjmJZKW7XEd+NiurGLkCyR1+dUPsYR7Q=";
  };

  nodejs = nodejs_24;
  npmDepsHash = "sha256-xjzcKNldoy2G3kYreXC4Xg2+9W4aC8KGndMuvMbGX1I=";

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
