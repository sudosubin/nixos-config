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
  version = "0.55.3";

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
        hash = "sha256-G5XVLmTcS8H811nxQMr726iaMnqHFJORFvth/TZ8ohs=";
      };
      x86_64-darwin = fetchurl {
        url = "https://github.com/badlogic/pi-mono/releases/download/v${finalAttrs.version}/pi-darwin-x64.tar.gz";
        hash = "sha256-/LCYggFKkm8tXEnMCBMMkFt2IZrZbHz/aI9rgY3E6/M=";
      };
      aarch64-linux = fetchurl {
        url = "https://github.com/badlogic/pi-mono/releases/download/v${finalAttrs.version}/pi-linux-arm64.tar.gz";
        hash = "sha256-p3IQmSV5ZbKHkQks06o0TCEO5RVIb6LJiVvq0G6YjkY=";
      };
      x86_64-linux = fetchurl {
        url = "https://github.com/badlogic/pi-mono/releases/download/v${finalAttrs.version}/pi-linux-x64.tar.gz";
        hash = "sha256-Az8qDfnLk6y667/1DbLuf64nSWcrPP5mpOqgY7yOMTY=";
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
