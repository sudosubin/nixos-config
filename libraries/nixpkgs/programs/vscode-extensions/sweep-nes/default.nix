{
  bun,
  cacert,
  fetchFromGitHub,
  lib,
  nix-update-script,
  stdenv,
  sweep-autocomplete,
}:

stdenv.mkDerivation (finalAttrs: {
  pname = "vscode-extension-sweep-nes";
  version = "0.5.0-unstable-2026-02-13";

  src = fetchFromGitHub {
    owner = "sweepai";
    repo = "vscode-nes";
    rev = "fa52a26b31d755c3e3d8e1f2d857a77d39cfebbb";
    hash = "sha256-oIW8D1oCBvgVmRZrmp7jNgUvebPqCI2eVlSeMRzdGBI=";
  };

  nativeBuildInputs = [ bun ];

  patches = [ ./use-nix-sweep-autocomplete.patch ];

  postPatch = ''
    substituteInPlace src/services/local-server.ts \
      --replace-fail "@sweep-autocomplete-bin@" "${lib.getExe sweep-autocomplete}"
  '';

  dontConfigure = true;
  dontFixup = true;

  buildPhase = ''
    runHook preBuild
    export HOME=$TMPDIR
    cp -r ${finalAttrs.passthru.bunDeps} node_modules
    chmod -R u+w node_modules
    bun build src/extension/activate.ts \
      --outfile=out/extension.js \
      --external=vscode \
      --format=cjs \
      --target=node
    runHook postBuild
  '';

  installPrefix = "share/vscode/extensions/sweepai.sweep-nes";

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/$installPrefix"
    cp package.json README.md "$out/$installPrefix/"
    cp -r out assets "$out/$installPrefix/"
    runHook postInstall
  '';

  passthru = {
    bunDeps = stdenv.mkDerivation {
      pname = "sweep-nes-bun-deps";
      version = finalAttrs.version;
      inherit (finalAttrs) src;
      nativeBuildInputs = [
        bun
        cacert
      ];
      dontConfigure = true;
      dontFixup = true;
      outputHashAlgo = "sha256";
      outputHashMode = "recursive";
      outputHash = "sha256-A+obfVP1Bl7IDLi8b2gdKof//tHtOOPbOH1F/MBWIOw=";
      buildPhase = ''
        runHook preBuild
        export HOME=$TMPDIR
        bun install --frozen-lockfile --production
        runHook postBuild
      '';
      installPhase = ''
        runHook preInstall
        cp -r node_modules $out
        runHook postInstall
      '';
    };

    vscodeExtPublisher = "sweepai";
    vscodeExtName = "sweep-nes";
    vscodeExtUniqueId = "sweepai.sweep-nes";

    updateScript = nix-update-script {
      extraArgs = [
        "--version=branch=main"
        "--subpackage=passthru.bunDeps"
      ];
    };
  };

  meta = {
    description = "Sweep next edit suggestions for VSCode";
    homepage = "https://github.com/sweepai/vscode-nes";
    license = lib.licenses.unlicense;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = lib.platforms.unix;
  };
})
