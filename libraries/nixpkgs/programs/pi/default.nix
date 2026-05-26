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
  version = "0.75.5";

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
        hash = "sha256-648DnEHoexQxyCuql/gHxNORt31m7LQeCWJwrjb5Ni0=";
      };
      x86_64-darwin = fetchurl {
        url = "https://github.com/badlogic/pi-mono/releases/download/v${finalAttrs.version}/pi-darwin-x64.tar.gz";
        hash = "sha256-JVbFFmtJW4OArlC1ntYc8ubE19IxwN8O0hTZ3kn0faw=";
      };
      aarch64-linux = fetchurl {
        url = "https://github.com/badlogic/pi-mono/releases/download/v${finalAttrs.version}/pi-linux-arm64.tar.gz";
        hash = "sha256-i1xm/Duu5f6kB39iMH95LWKTZgMVs85NCUDEk1O0X1A=";
      };
      x86_64-linux = fetchurl {
        url = "https://github.com/badlogic/pi-mono/releases/download/v${finalAttrs.version}/pi-linux-x64.tar.gz";
        hash = "sha256-rGh6zXJwXavpZ/1A02Uxf2gFSHi+HLLArpoFkv0Qi10=";
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
