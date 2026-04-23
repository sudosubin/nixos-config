#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils common-updater-scripts
set -eu -o pipefail

latestVersion=$(curl -fsSL https://desktop.figma.com/agent/mac/RELEASE.json | jq -r '.version')
latestArmVersion=$(curl -fsSL https://desktop.figma.com/agent/mac-arm/RELEASE.json | jq -r '.version')
currentVersion=$(nix eval --raw -f . figma-agent.version)

if [[ "$latestVersion" != "$latestArmVersion" ]]; then
  echo "mac version mismatch: $latestVersion != $latestArmVersion"
  exit 1
fi

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

declare -A channels=( [aarch64-darwin]="mac-arm" [x86_64-darwin]="mac" )

for platform in "${!channels[@]}"; do
  url="https://desktop.figma.com/agent/${channels[$platform]}/FigmaAgent-$latestVersion.zip"
  source=$(nix-prefetch-url "$url")
  hash=$(nix-hash --to-sri --type sha256 "$source")
  update-source-version figma-agent "$latestVersion" "$hash" \
    --system="$platform" \
    --source-key="passthru.sources.$platform" \
    --ignore-same-version
done
