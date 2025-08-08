{
  lib,
  fetchurl,
  stdenvNoCC,
  autoPatchelfHook,
  makeWrapper,
}:

stdenvNoCC.mkDerivation (
  finalAttrs:
  let
    version = "2025.08.08-562252e";

    sources = {
      "x86_64-linux" = {
        url = "https://downloads.cursor.com/lab/${version}/linux/x64/agent-cli-package.tar.gz";
        sha256 = "1rf4xvbx5sb9x9gwddblq2r4n2zn4p3szdbjyzfzianq2hwxig5l";
      };
      "aarch64-linux" = {
        url = "https://downloads.cursor.com/lab/${version}/linux/arm64/agent-cli-package.tar.gz";
        sha256 = "0fkzb9b8h7rvrnc9chskf5k1afgn8psagcbwpgwqksdli0d9wxfz";
      };
      "x86_64-darwin" = {
        url = "https://downloads.cursor.com/lab/${version}/darwin/x64/agent-cli-package.tar.gz";
        sha256 = "0mqqidrb46w8i8jhdp7xs060pm2v87y8w527qsmpwxm49irb18h7";
      };
      "aarch64-darwin" = {
        url = "https://downloads.cursor.com/lab/${version}/darwin/arm64/agent-cli-package.tar.gz";
        sha256 = "0c0w30rlzphs4vxm6059hzmmnq34rcayrjrpa0d5rdbvdhrv41mw";
      };
    };

  in
  {
    pname = "cursor-agent";
    inherit version;

    src = fetchurl {
      inherit (sources.${stdenvNoCC.hostPlatform.system}) url sha256;
    };

    nativeBuildInputs = lib.optionals stdenvNoCC.hostPlatform.isLinux [ autoPatchelfHook ];

    installPhase = ''
      runHook preInstall

      mkdir -p $out/bin $out/share/cursor-agent
      cp -r * $out/share/cursor-agent/
      ln -s $out/share/cursor-agent/cursor-agent $out/bin/cursor-agent

      runHook postInstall
    '';

    meta = {
      description = "Cursor Agent";
      homepage = "https://cursor.com/";
      license = lib.licenses.unfree;
      maintainers = with lib.maintainers; [ sudosubin ];
      platforms = builtins.attrNames sources;
      mainProgram = "cursor-agent";
    };
  }
)
