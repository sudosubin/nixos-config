#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils common-updater-scripts
set -eu -o pipefail

latestVersion=$(
  curl -s https://www.homerow.app/appcast.xml \
    | grep -m2 "title" \
    | tail -n1 \
    | sed -r "s|.*>([0-9.]+)<.*|\1|g"
)
currentVersion=$(nix eval --raw -f . homerow.version)

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

url="https://builds.homerow.app/v$latestVersion/Homerow.zip"
source=$(nix-prefetch-url "$url" --unpack)
hash=$(nix-hash --to-sri --type sha256 "$source")
update-source-version homerow "$latestVersion" "$hash"
