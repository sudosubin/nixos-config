#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils common-updater-scripts
set -eu -o pipefail

latestVersion=$(curl -s https://api.github.com/repos/schpet/linear-cli/releases/latest | jq -r '.tag_name | sub("^v"; "")')
currentVersion=$(nix eval --raw -f . linear-cli.version)

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

declare -A platforms=( [aarch64-darwin]="aarch64-apple-darwin" [x86_64-darwin]="x86_64-apple-darwin" [aarch64-linux]="aarch64-unknown-linux-gnu" [x86_64-linux]="x86_64-unknown-linux-gnu" )

for platform in "${!platforms[@]}"; do
  url="https://github.com/schpet/linear-cli/releases/download/v$latestVersion/linear-${platforms[$platform]}.tar.xz"
  source=$(nix-prefetch-url "$url" --unpack)
  hash=$(nix-hash --to-sri --type sha256 "$source")
  update-source-version linear-cli "$latestVersion" "$hash" \
    --system="$platform" \
    --source-key="passthru.sources.$platform" \
    --ignore-same-version
done
