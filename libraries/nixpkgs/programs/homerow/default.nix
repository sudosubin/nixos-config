{ lib, stdenvNoCC, fetchzip, curl, jq, runCommand }:

let
  fetchFromAppCenter = { owner, app, group, version }:
    runCommand "fetchFromAppCenter" { buildInputs = [ curl jq ]; } ''
      RELEASE_ID=$(
        curl -k "https://install.appcenter.ms/api/v0.1/apps/${owner}/${app}/distribution_groups/${group}/public_releases" \
          -H "user-agent: Chrome/0.0.0.0" \
          | jq -r ".[] | select(.short_version == \"${version}\") | .id"
      )
      DOWNLOAD_URL=$(
        curl -k "https://install.appcenter.ms/api/v0.1/apps/${owner}/${app}/distribution_groups/${group}/releases/$RELEASE_ID" \
          -H "user-agent: Chrome/0.0.0.0" \
          | jq -r ".download_url"
      )
      echo "$DOWNLOAD_URL" > "$out"
    '';

in
stdenvNoCC.mkDerivation rec {
  pname = "homerow";
  version = "0.21";

  src = fetchzip {
    url = builtins.readFile (fetchFromAppCenter {
      inherit version;
      owner = "dexterleng";
      app = "homerow-redux";
      group = "production";
    });
    name = "Homerow.app";
    extension = "zip";
    sha256 = "0g7p82l49gi8cbrk16dzkfrh2gq9hda351rq9mz8szyg169gz32g";
  };

  sourceRoot = "Homerow.app";

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/Applications/${sourceRoot}"
    cp -R . "$out/Applications/${sourceRoot}"
    runHook postInstall
  '';

  meta = with lib; {
    homepage = "https://homerow.app";
    description = "Keyboard shortcuts for every button in macOS";
    license = licenses.unfree;
    platforms = platforms.darwin;
    maintainers = [ maintainers.sudosubin ];
  };
}
