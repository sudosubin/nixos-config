#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils common-updater-scripts
set -eu -o pipefail

latestVersion=$(
  curl -fsSL \
    -H "Accept: application/vnd.github+json" \
    ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
    "https://api.github.com/repos/stablyai/orca/releases/latest" \
      | jq -er ".tag_name | ltrimstr(\"v\")"
)
currentVersion=$(nix eval --raw -f . orca.version)

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

declare -A assets=( [aarch64-darwin]="arm64-mac" [x86_64-darwin]="mac" )

for platform in "${!assets[@]}"; do
  url="https://github.com/stablyai/orca/releases/download/v$latestVersion/Orca-$latestVersion-${assets[$platform]}.zip"
  source=$(nix-prefetch-url --unpack "$url")
  hash=$(nix-hash --to-sri --type sha256 "$source")
  update-source-version orca "$latestVersion" "$hash" \
    --system="$platform" \
    --source-key="passthru.sources.$platform" \
    --ignore-same-version
done
