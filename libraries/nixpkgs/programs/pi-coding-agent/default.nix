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
  pname = "pi-coding-agent";
  version = "0.50.1";

  src = fetchFromGitHub {
    owner = "badlogic";
    repo = "pi-mono";
    rev = "v${finalAttrs.version}";
    hash = "sha256-c+Utd/0CY+iXFr8ICgvEtLmrXb3HVXzscWOitbOFipY=";
  };

  node_modules = stdenv.mkDerivation {
    inherit (finalAttrs) version src;
    pname = "${finalAttrs.pname}-node_modules";

    nativeBuildInputs = [ bun ];

    buildPhase = ''
      bun install --ignore-scripts --no-progress
    '';

    installPhase = ''
      mkdir -p $out
      cp -R ./node_modules $out/
    '';

    outputHash = "sha256-ghaZAuP1vcUqsbFWj7tJScQYoIMyIeO/2A7HsiJ0Cd0=";
    outputHashMode = "recursive";
  };

  nativeBuildInputs = [
    bun
    nodejs-slim
    makeWrapper
  ];

  configurePhase = ''
    cp -R ${finalAttrs.node_modules}/node_modules .
    chmod -R +w node_modules
  '';

  patchPhase = ''
    substituteInPlace packages/ai/package.json \
      --replace-fail "npm run generate-models && " ""
  '';

  buildPhase = ''
    bun run build
    (cd packages/coding-agent && bun run build:binary)
  '';

  installPhase = ''
    mkdir -p $out/lib/pi-coding-agent $out/bin
    cp -r packages/coding-agent/dist/* $out/lib/pi-coding-agent

    wrapProgram $out/lib/pi-coding-agent/pi --suffix PATH : ${
      lib.makeBinPath [
        fd
        ripgrep
      ]
    }

    ln -s $out/lib/pi-coding-agent/pi $out/bin/pi
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
