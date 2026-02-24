{
  lib,
  stdenvNoCC,
  fetchFromGitHub,
  makeBinaryWrapper,
  nix-update-script,
  nodejs_24,
  pnpm,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "ccusage";
  version = "18.0.6";

  src = fetchFromGitHub {
    owner = "ryoppippi";
    repo = "ccusage";
    tag = "v${finalAttrs.version}";
    hash = "sha256-l03LLiyrfIynp4BOz/CF9TqYPxesnh0aHJIIm7VCX3c=";
  };

  nativeBuildInputs = [
    nodejs_24
    pnpm.configHook
    makeBinaryWrapper
  ];

  pnpmWorkspaces = [
    "ccusage"
    "@ccusage/terminal"
    "@ccusage/internal"
  ];

  pnpmDeps = pnpm.fetchDeps {
    inherit (finalAttrs)
      pname
      version
      src
      pnpmWorkspaces
      ;
    fetcherVersion = 2;
    hash = "sha256-Bmae7d9yVTfaiON0f7lriDR89s8pGQbPYuGOZs6qER4=";
  };

  postPatch = ''
    substituteInPlace apps/ccusage/package.json \
      --replace-fail '"build": "pnpm run generate:schema && tsdown"' '"build": "tsdown"'
  '';

  buildPhase = ''
    runHook preBuild

    pnpm run --filter ccusage... build

    rm node_modules/.modules.yaml
    rm node_modules/.pnpm-workspace-state-v1.json
    find . -type d -name .bin -exec rm -r {} +

    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall

    mkdir -p $out/{bin,lib/ccusage/apps}
    cp -r apps/ccusage $out/lib/ccusage/apps/
    cp -r node_modules package.json packages $out/lib/ccusage/

    makeWrapper ${lib.getExe nodejs_24} $out/bin/ccusage \
      --inherit-argv0 \
      --add-flags $out/lib/ccusage/apps/ccusage/dist/index.js

    runHook postInstall
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "CLI tool for analyzing Claude Code usage from local JSONL files";
    homepage = "https://ccusage.com";
    changelog = "https://github.com/ryoppippi/ccusage/releases/tag/v${finalAttrs.version}";
    license = lib.licenses.mit;
    platforms = lib.platforms.all;
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = "ccusage";
  };
})
