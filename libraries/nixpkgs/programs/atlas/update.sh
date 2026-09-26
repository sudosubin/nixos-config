#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils common-updater-scripts
set -eu -o pipefail

latestTag=$(
  curl -fsSL \
    -H "Accept: application/vnd.github+json" \
    ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
    "https://api.github.com/repos/pacifio/atlas/releases/latest" |
    jq -er ".tag_name"
)

# Upstream tags releases as "<channel>-<version>", e.g. "alpha-0.3.3"
if [[ "$latestTag" != alpha-* ]]; then
  echo "unexpected release tag '$latestTag': update the url prefix in default.nix" >&2
  exit 1
fi

latestVersion="${latestTag#alpha-}"
currentVersion=$(nix eval --raw -f . atlas.version)

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

declare -A platforms=([aarch64 - darwin]="aarch64")

for platform in "${!platforms[@]}"; do
  url="https://github.com/pacifio/atlas/releases/download/$latestTag/Atlas_${latestVersion}_${platforms[$platform]}.dmg"
  source=$(nix-prefetch-url "$url")
  hash=$(nix-hash --to-sri --type sha256 "$source")
  update-source-version atlas "$latestVersion" "$hash" \
    --system="$platform" \
    --source-key="passthru.sources.$platform" \
    --ignore-same-version
done
