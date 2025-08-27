{
  lib,
  fetchurl,
  stdenv,
  autoPatchelfHook,
}:

let
  inherit (stdenv) hostPlatform;
  version = "2025.08.25-896bbe1";

  sources = {
    x86_64-linux = fetchurl {
      url = "https://downloads.cursor.com/lab/${version}/linux/x64/agent-cli-package.tar.gz";
      sha256 = "1ibv1rn7bxj7vpmm86sa5a56ifsd80yg8yvhb94xb4702h4rdf0a";
    };
    aarch64-linux = fetchurl {
      url = "https://downloads.cursor.com/lab/${version}/linux/arm64/agent-cli-package.tar.gz";
      sha256 = "07h7qhp0d8m48fabnvilk9dx2glpd25xblifpi25bwsapbaizvwa";
    };
    x86_64-darwin = fetchurl {
      url = "https://downloads.cursor.com/lab/${version}/darwin/x64/agent-cli-package.tar.gz";
      sha256 = "04as3h2blf9zfvvfh67c4qlkc82jnklnb6isp1276v6lv675wgxz";
    };
    aarch64-darwin = fetchurl {
      url = "https://downloads.cursor.com/lab/${version}/darwin/arm64/agent-cli-package.tar.gz";
      sha256 = "1dxzg5l0gxkrrd62432rqliikhq24h3qncq2lai8yk1iagq09rxc";
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
