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
  version = "0.70.6";

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
        hash = "sha256-grGelWpG5cC5eS6xOFtbYYvzGPXYrSLiZDnUo2q4lAI=";
      };
      x86_64-darwin = fetchurl {
        url = "https://github.com/badlogic/pi-mono/releases/download/v${finalAttrs.version}/pi-darwin-x64.tar.gz";
        hash = "sha256-A7Nt+Gc9twYKzqMq2UJOZXCyTd663CcQ84+VmZql7EQ=";
      };
      aarch64-linux = fetchurl {
        url = "https://github.com/badlogic/pi-mono/releases/download/v${finalAttrs.version}/pi-linux-arm64.tar.gz";
        hash = "sha256-JnIUDlHJ7WQmpV1ub/bpjx5cJNDkJtBznRvhWSlX0nE=";
      };
      x86_64-linux = fetchurl {
        url = "https://github.com/badlogic/pi-mono/releases/download/v${finalAttrs.version}/pi-linux-x64.tar.gz";
        hash = "sha256-MrW4lEtbTaDtST8CpKtxL6JFagDm24REtGCgJKc7HOw=";
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
