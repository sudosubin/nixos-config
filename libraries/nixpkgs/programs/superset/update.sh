#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils common-updater-scripts
set -eu -o pipefail

latestVersion=$(
  curl -s https://api.github.com/repos/superset-sh/superset/releases?per_page=20 \
    | jq -r '[.[] | select(.tag_name | test("^desktop-v[0-9]+\\.[0-9]+\\.[0-9]+$"))][0].tag_name | sub("^desktop-v"; "")'
)
currentVersion=$(nix eval --raw -f . superset.version)

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

declare -A platforms=(
  [x86_64-linux]="Superset-x86_64.AppImage"
  [aarch64-darwin]="Superset-arm64-mac.zip"
  [x86_64-darwin]="Superset-x64-mac.zip"
)

for platform in "${!platforms[@]}"; do
  url="https://github.com/superset-sh/superset/releases/download/desktop-v$latestVersion/${platforms[$platform]}"
  source=$(nix-prefetch-url "$url")
  hash=$(nix-hash --to-sri --type sha256 "$source")
  update-source-version superset "$latestVersion" "$hash" \
    --system="$platform" \
    --source-key="passthru.sources.$platform" \
    --ignore-same-version
done
