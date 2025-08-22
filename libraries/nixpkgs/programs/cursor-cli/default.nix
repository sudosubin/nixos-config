{
  lib,
  fetchurl,
  stdenv,
  autoPatchelfHook,
}:

let
  inherit (stdenv) hostPlatform;
  version = "2025.08.21-9ba2c98";

  sources = {
    x86_64-linux = fetchurl {
      url = "https://downloads.cursor.com/lab/${version}/linux/x64/agent-cli-package.tar.gz";
      sha256 = "0q9zjbsz218vmxp8vxipvbrjy4379lj04hwc4gnkxdsrkblyhfxg";
    };
    aarch64-linux = fetchurl {
      url = "https://downloads.cursor.com/lab/${version}/linux/arm64/agent-cli-package.tar.gz";
      sha256 = "0vb44gcjr6i4m6ywx920xb57hiqgnr7sxvyhxgj2nmxdq4h6675l";
    };
    x86_64-darwin = fetchurl {
      url = "https://downloads.cursor.com/lab/${version}/darwin/x64/agent-cli-package.tar.gz";
      sha256 = "12y63vli14jkhkhyl92l8qmv5x9rhfyja4cm40an676r8i04wd5c";
    };
    aarch64-darwin = fetchurl {
      url = "https://downloads.cursor.com/lab/${version}/darwin/arm64/agent-cli-package.tar.gz";
      sha256 = "0g77csrxbjmjqcb4jdx3z3ni084x33fd5rvx0p356ai9xjxqb33b";
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
