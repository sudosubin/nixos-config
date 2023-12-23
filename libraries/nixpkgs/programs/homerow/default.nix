{ lib, stdenvNoCC, curl, jq, unzip, runCommand }:

let
  fetchFromAppCenter = { owner, app, group, version }:
    runCommand "fetchFromAppCenter" { buildInputs = [ curl jq ]; } ''
      RELEASE_ID=$(
        curl -k "https://install.appcenter.ms/api/v0.1/apps/${owner}/${app}/distribution_groups/${group}/public_releases" \
          -H "user-agent: Chrome/118.0.0.0" \
          | jq -r ".[] | select(.short_version == \"0.21\") | .id"
      )
      DOWNLOAD_URL=$(
        curl -k "https://install.appcenter.ms/api/v0.1/apps/${owner}/${app}/distribution_groups/${group}/releases/$RELEASE_ID" \
          -H "user-agent: Chrome/118.0.0.0" \
          | jq -r ".download_url"
      )
      curl -kL "$DOWNLOAD_URL" -o "$out"
    '';

in
stdenvNoCC.mkDerivation rec {
  pname = "homerow";
  version = "0.21";

  src = fetchFromAppCenter {
    inherit version;
    owner = "dexterleng";
    app = "homerow-redux";
    group = "production";
  };

  sourceRoot = "Homerow.app";

  nativeBuildInputs = [ unzip ];

  unpackPhase = ''
    unzip $src
  '';

  installPhase = ''
    mkdir -p "$out/Applications/${sourceRoot}"
    cp -R . "$out/Applications/${sourceRoot}"
  '';

  meta = with lib; {
    homepage = "https://www.homerow.app/";
    description = "Spotlight for the macOS user interface";
    license = licenses.unfree;
    platforms = platforms.darwin;
    maintainers = [ maintainers.sudosubin ];
  };
}
