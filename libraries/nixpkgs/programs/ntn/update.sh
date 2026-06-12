#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl coreutils gawk nix common-updater-scripts
set -eu -o pipefail

latestVersion=$(curl -fsSL "https://ntn.dev/latest.txt" | tr -d '[:space:]' | sed 's/^v//')
currentVersion=$(nix eval --raw -f . ntn.version)

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

declare -A targets=(
  [aarch64-darwin]="aarch64-apple-darwin"
  [x86_64-darwin]="x86_64-apple-darwin"
  [aarch64-linux]="aarch64-unknown-linux-musl"
  [x86_64-linux]="x86_64-unknown-linux-musl"
)

for platform in "${!targets[@]}"; do
  target="${targets[$platform]}"
  checksumUrl="https://ntn.dev/releases/v$latestVersion/ntn-$target.tar.gz.sha256"

  hex=$(curl -fsSL "$checksumUrl" | awk '{print $1}')
  hash=$(nix hash convert --hash-algo sha256 --to sri "$hex")

  update-source-version ntn "$latestVersion" "$hash" \
    --system="$platform" \
    --source-key="passthru.sources.$platform" \
    --ignore-same-version
done
