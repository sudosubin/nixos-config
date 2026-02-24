#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils common-updater-scripts
set -eu -o pipefail

latestVersion=$(curl -s https://api.github.com/repos/badlogic/pi-mono/releases/latest | jq -r ".tag_name | ltrimstr(\"v\")")
currentVersion=$(nix eval --raw -f . pi.version)

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

declare -A platforms=(
  [aarch64-darwin]="darwin-arm64"
  [x86_64-darwin]="darwin-x64"
  [aarch64-linux]="linux-arm64"
  [x86_64-linux]="linux-x64"
)

for platform in "${!platforms[@]}"; do
  url="https://github.com/badlogic/pi-mono/releases/download/v$latestVersion/pi-${platforms[$platform]}.tar.gz"
  source=$(nix-prefetch-url "$url")
  hash=$(nix-hash --to-sri --type sha256 "$source")
  update-source-version pi "$latestVersion" "$hash" \
    --system="$platform" \
    --source-key="passthru.sources.$platform" \
    --ignore-same-version
done
