{
  lib,
  stdenv,
  fetchFromGitHub,
  bun,
  nodejs-slim,
  fd,
  ripgrep,
  makeWrapper,
  nix-update-script,
}:

stdenv.mkDerivation (finalAttrs: {
  pname = "pi";
  version = "0.52.8";

  src = fetchFromGitHub {
    owner = "badlogic";
    repo = "pi-mono";
    rev = "v${finalAttrs.version}";
    hash = "sha256-HygE4ch4u8EQ19qL0a5YqUfVNKzleinYjK0uRRqmwBc=";
  };

  node_modules = stdenv.mkDerivation {
    inherit (finalAttrs) version src;
    pname = "${finalAttrs.pname}-node_modules";

    nativeBuildInputs = [ bun ];

    buildPhase = ''
      bun install --ignore-scripts --no-cache --no-progress
    '';

    installPhase = ''
      mkdir -p $out
      rm -rf ./node_modules/.cache
      cp -R ./node_modules ./packages $out/
    '';

    dontPatchShebangs = true;

    outputHash = "sha256-bkTj7V3C1xVXDQt4FTOPRXp5xyHvdDyj7uk3/YL2D/M=";
    outputHashMode = "recursive";
  };

  nativeBuildInputs = [
    bun
    nodejs-slim
    makeWrapper
  ];

  configurePhase = ''
    cp -R ${finalAttrs.node_modules}/{node_modules,packages} .
    chmod -R +w node_modules packages
  '';

  buildPhase = ''
    substituteInPlace packages/ai/package.json \
      --replace-fail "npm run generate-models && " ""

    bun run build
    (cd packages/coding-agent && bun run build:binary)
  '';

  installPhase = ''
    mkdir -p $out/lib/pi $out/bin
    cp -r packages/coding-agent/dist/* $out/lib/pi

    wrapProgram $out/lib/pi/pi --suffix PATH : ${
      lib.makeBinPath [
        fd
        ripgrep
      ]
    }

    ln -s $out/lib/pi/pi $out/bin/pi
  '';

  passthru.updateScript = nix-update-script {
    extraArgs = [
      "--subpackage"
      "node_modules"
    ];
  };

  meta = {
    description = "Coding agent CLI with read, bash, edit, write tools and session management";
    homepage = "https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.unix;
    mainProgram = "pi";
  };
})
