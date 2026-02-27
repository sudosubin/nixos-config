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
  pname = "ccusage-pi";
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
    "@ccusage/pi"
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
    hash = "sha256-yKNyhk1MFEHiShBAhkeUGuCQSiK/fxzgSCx5F0lL2hA=";
  };

  buildPhase = ''
    runHook preBuild

    pnpm run --filter @ccusage/pi... build

    rm node_modules/.modules.yaml
    rm node_modules/.pnpm-workspace-state-v1.json
    find . -type d -name .bin -exec rm -r {} +

    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall

    mkdir -p $out/{bin,lib/ccusage-pi/apps}
    cp -r apps/pi $out/lib/ccusage-pi/apps/
    cp -r node_modules package.json packages $out/lib/ccusage-pi/

    makeWrapper ${lib.getExe nodejs_24} $out/bin/ccusage-pi \
      --inherit-argv0 \
      --add-flags $out/lib/ccusage-pi/apps/pi/dist/index.js

    runHook postInstall
  '';

  passthru.updateScript = nix-update-script { };

  meta = {
    description = "Pi-agent usage tracking - unified Claude Max usage across Claude Code and pi-agent";
    homepage = "https://ccusage.com";
    changelog = "https://github.com/ryoppippi/ccusage/releases/tag/v${finalAttrs.version}";
    license = lib.licenses.mit;
    platforms = lib.platforms.all;
    maintainers = with lib.maintainers; [ sudosubin ];
    mainProgram = "ccusage-pi";
  };
})
