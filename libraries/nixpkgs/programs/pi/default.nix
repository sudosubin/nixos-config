{
  fetchurl,
  lib,
  stdenvNoCC,
  autoPatchelfHook,
  fd,
  ripgrep,
  makeWrapper,
}:

stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "pi";
  version = "0.70.0";

  src = finalAttrs.passthru.sources.${stdenvNoCC.hostPlatform.system};

  sourceRoot = "pi";

  nativeBuildInputs = [
    makeWrapper
  ]
  ++ lib.optionals stdenvNoCC.hostPlatform.isLinux [ autoPatchelfHook ];

  installPhase = ''
    mkdir -p $out/lib/pi $out/bin
    cp -r . $out/lib/pi/

    wrapProgram $out/lib/pi/pi --suffix PATH : ${
      lib.makeBinPath [
        fd
        ripgrep
      ]
    }

    ln -s $out/lib/pi/pi $out/bin/pi
  '';

  passthru = {
    updateScript = ./update.sh;
    sources = {
      aarch64-darwin = fetchurl {
        url = "https://github.com/badlogic/pi-mono/releases/download/v${finalAttrs.version}/pi-darwin-arm64.tar.gz";
        hash = "sha256-k9/2D6a6C1Jy0eFVeO0CqJEpDjr9eztkjrsDM0h2zQY=";
      };
      x86_64-darwin = fetchurl {
        url = "https://github.com/badlogic/pi-mono/releases/download/v${finalAttrs.version}/pi-darwin-x64.tar.gz";
        hash = "sha256-gDRaKFc9lt3Rtx/S1sC9jvTgn1889t0R3akPm67WK2c=";
      };
      aarch64-linux = fetchurl {
        url = "https://github.com/badlogic/pi-mono/releases/download/v${finalAttrs.version}/pi-linux-arm64.tar.gz";
        hash = "sha256-+ZWMmmJfJp3ZEOivD4ERklNFDcLmGx5vM71KcnAhzrc=";
      };
      x86_64-linux = fetchurl {
        url = "https://github.com/badlogic/pi-mono/releases/download/v${finalAttrs.version}/pi-linux-x64.tar.gz";
        hash = "sha256-vDlGIUPDOIfEQ0SnD/rvss0+qjLewgdaojsF1xUX7uo=";
      };
    };
  };

  meta = {
    description = "Coding agent CLI with read, bash, edit, write tools and session management";
    homepage = "https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent";
    license = lib.licenses.mit;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = builtins.attrNames finalAttrs.passthru.sources;
    mainProgram = "pi";
  };
})
