{
  lib,
  fetchurl,
  stdenv,
  autoPatchelfHook,
}:

let
  inherit (stdenv) hostPlatform;
  version = "2025.08.09-d8191f3";

  sources = {
    x86_64-linux = fetchurl {
      url = "https://downloads.cursor.com/lab/${version}/linux/x64/agent-cli-package.tar.gz";
      sha256 = "1nzil47r5rsi5cjkfhfcjj9p0w7nv76qpf204s41l61x807kmcmh";
    };
    aarch64-linux = fetchurl {
      url = "https://downloads.cursor.com/lab/${version}/linux/arm64/agent-cli-package.tar.gz";
      sha256 = "1w0cr1dh43p3j9fm5cpnzzykc55igc0v8vx1djj0h7l81kpb9s79";
    };
    x86_64-darwin = fetchurl {
      url = "https://downloads.cursor.com/lab/${version}/darwin/x64/agent-cli-package.tar.gz";
      sha256 = "1lhxsriyymq346zw3ws45vn5ak7jl9zpag2aab0zxnhv22cmis6f";
    };
    aarch64-darwin = fetchurl {
      url = "https://downloads.cursor.com/lab/${version}/darwin/arm64/agent-cli-package.tar.gz";
      sha256 = "0a1zy96cwaaglwvcj5jpqc5c5bsq60fixnbn4z8y39f90pqy4gdz";
    };
  };
in
stdenv.mkDerivation {
  pname = "cursor-cli";
  inherit version;

  src = sources.${hostPlatform.system};

  nativeBuildInputs = lib.optionals hostPlatform.isLinux [
    autoPatchelfHook
    stdenv.cc.cc.lib
  ];

  installPhase = ''
    runHook preInstall

    mkdir -p $out/bin $out/share/cursor-agent
    cp -r * $out/share/cursor-agent/
    ln -s $out/share/cursor-agent/cursor-agent $out/bin/cursor-agent

    runHook postInstall
  '';

  passthru.updateScript = ./update.sh;

  meta = {
    description = "Cursor CLI";
    homepage = "https://cursor.com/cli";
    license = lib.licenses.unfree;
    maintainers = with lib.maintainers; [ sudosubin ];
    platforms = builtins.attrNames sources;
    mainProgram = "cursor-agent";
  };
}
