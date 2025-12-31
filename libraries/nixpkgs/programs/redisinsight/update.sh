#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils common-updater-scripts
set -eu -o pipefail

latestVersion=$(curl -s https://api.github.com/repos/redis/RedisInsight/releases/latest | jq -r ".tag_name")
currentVersion=$(nix eval --raw -f . redisinsight.version)

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

declare -A platforms=( [aarch64-darwin]="arm64" [x86_64-darwin]="x64" )

for platform in "${!platforms[@]}"; do
  url="https://s3.amazonaws.com/redisinsight.download/public/releases/$latestVersion/Redis-Insight-mac-${platforms[$platform]}.dmg"
  source=$(nix-prefetch-url "$url")
  hash=$(nix-hash --to-sri --type sha256 "$source")
  update-source-version redisinsight "$latestVersion" "$hash" \
    --system="$platform" \
    --source-key="passthru.sources.$platform" \
    --ignore-same-version
done
