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
  version = "18.0.8";

  src = fetchFromGitHub {
    owner = "ryoppippi";
    repo = "ccusage";
    tag = "v${finalAttrs.version}";
    hash = "sha256-YxT2RVa0RaCepod+ZRLk3qoF5YguZLbjozDmJ4Om2tk=";
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
    hash = "sha256-nygy6LEb1AMDFdDkJZ0zHCX3r2DAJM7PylzUNgOO8Hc=";
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
