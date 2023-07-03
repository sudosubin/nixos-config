final: { lib, fetchzip, stdenvNoCC, makeWrapper, deno, ... }@prev:

let
  version = "2.5.0";

  sources = {
    darwin = {
      url = "https://downloads.slack-edge.com/slack-cli/slack_cli_${version}_macOS_64-bit.tar.gz";
      sha256 = "sha256-gKjkVHNviYdA8ctOnonCzl2vzqSCdqF+kxTrkN4dI6Q=";
    };

    linux = {
      url = "https://downloads.slack-edge.com/slack-cli/slack_cli_${version}_linux_64-bit.tar.gz";
      sha256 = "";
    };
  };

in
{
  slack-cli-bin = stdenvNoCC.mkDerivation rec {
    pname = "slack-cli-bin";
    inherit version;

    src = fetchzip (if stdenvNoCC.isDarwin then sources.darwin else sources.linux);

    nativeBuildInputs = [ makeWrapper ];

    installPhase = ''
      mkdir -p $out/bin
      cp slack $out/bin/slack
      runHook postInstall
    '';

    postInstall = ''
      wrapProgram $out/bin/slack --prefix PATH : ${lib.makeBinPath [ deno ]}
    '';

    meta = with lib; {
      homepage = "https://api.slack.com/future";
      description = "CLI to create, run, and deploy Slack apps";
      license = licenses.unfree;
      platforms = platforms.unix;
      maintainers = [ maintainers.sudosubin ];
    };
  };
}
