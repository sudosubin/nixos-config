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
  version = "0.54.0";

  src = fetchFromGitHub {
    owner = "badlogic";
    repo = "pi-mono";
    rev = "v${finalAttrs.version}";
    hash = "sha256-j8h8KKt/1m47Y6/KA8g213gooq0n2fAqBVkKhHsBCGw=";
  };

  patches = [ ./prevent-empty-pi.patch ];

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

    outputHash = "sha256-hdUnxWSxJAc0cFF/QCCrC4tv2IKdnumEz8Qms1pUm8s=";
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
