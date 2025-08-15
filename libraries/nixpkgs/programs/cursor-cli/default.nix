{
  lib,
  fetchurl,
  stdenv,
  autoPatchelfHook,
}:

let
  inherit (stdenv) hostPlatform;
  version = "2025.08.15-dbc8d73";

  sources = {
    x86_64-linux = fetchurl {
      url = "https://downloads.cursor.com/lab/${version}/linux/x64/agent-cli-package.tar.gz";
      sha256 = "0k44x70yk8pbykqz7v9nsq3x6jn7xiyqx744w8kc4vxvymzvvbpi";
    };
    aarch64-linux = fetchurl {
      url = "https://downloads.cursor.com/lab/${version}/linux/arm64/agent-cli-package.tar.gz";
      sha256 = "02hqfsl8dy6b3jqqvf35w911klaj3403g0fc2plm4bkhh6xjiamq";
    };
    x86_64-darwin = fetchurl {
      url = "https://downloads.cursor.com/lab/${version}/darwin/x64/agent-cli-package.tar.gz";
      sha256 = "17qjhchz806p45bcpm47qvjp6zgckjckihxab926xpvs2ycxpp94";
    };
    aarch64-darwin = fetchurl {
      url = "https://downloads.cursor.com/lab/${version}/darwin/arm64/agent-cli-package.tar.gz";
      sha256 = "07r0y5wckan208bqdghdszxc11b7p73r2bn0m68asnvil2hb5ig5";
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
