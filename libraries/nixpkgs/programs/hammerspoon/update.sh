#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils common-updater-scripts
set -eu -o pipefail

# Hammerspoon renumbered its releases (e.g. 1.4.27 predates 1.1.1)
latestVersion=$(
  curl -fsSL \
    -H "Accept: application/vnd.github+json" \
    ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
    "https://api.github.com/repos/Hammerspoon/hammerspoon/releases/latest" \
      | jq -er ".tag_name"
)
currentVersion=$(nix eval --raw -f . hammerspoon.version)

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

url="https://github.com/Hammerspoon/hammerspoon/releases/download/$latestVersion/Hammerspoon-$latestVersion.zip"
source=$(nix-prefetch-url "$url" --unpack)
hash=$(nix-hash --to-sri --type sha256 "$source")
update-source-version hammerspoon "$latestVersion" "$hash"
