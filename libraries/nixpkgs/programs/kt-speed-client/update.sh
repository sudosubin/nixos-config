#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils common-updater-scripts
set -eu -o pipefail

systemOptionPath=$(
  curl -fsSL https://speed.kt.com/ \
    | grep -m1 -oE '/assets/systemOption-[^" ]+\.js'
)
latestVersion=$(
  curl -fsSL "https://speed.kt.com$systemOptionPath" \
    | grep -m1 -oE 'macVersion:`[0-9][0-9.]*`' \
    | grep -oE '[0-9][0-9.]*' \
    | head -n1
)
currentVersion=$(nix eval --raw -f . kt-speed-client.version)

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

url="https://speed.kt.com/file/ktspeed.pkg"
source=$(nix-prefetch-url "$url")
hash=$(nix-hash --to-sri --type sha256 "$source")
update-source-version kt-speed-client "$latestVersion" "$hash"
