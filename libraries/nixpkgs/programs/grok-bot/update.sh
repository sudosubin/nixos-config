#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils common-updater-scripts
set -eu -o pipefail

updateApi="https://api2.cursor.sh/updates/api/update"
latestVersion=$(curl -fsSL "$updateApi/darwin-arm64/sand/0.0.0/stable" | jq -er '.name')
currentVersion=$(nix eval --raw -f . grok-bot.version)

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

declare -A platforms=(
  [aarch64-darwin]="darwin-arm64"
  [aarch64-linux]="linux-arm64"
  [x86_64-linux]="linux-x64"
)
declare -A urls hashes

# Check all platform versions and prefetch sources before changing the derivation.
for platform in "${!platforms[@]}"; do
  target="${platforms[$platform]}"
  release=$(curl -fsSL "$updateApi/$target/sand/0.0.0/stable")
  platformVersion=$(jq -er '.name // .version' <<< "$release")
  if [[ "$platformVersion" != "$latestVersion" ]]; then
    echo "Version mismatch for $platform: expected $latestVersion, got $platformVersion" >&2
    exit 1
  fi

  if [[ "$platform" == *-darwin ]]; then
    urls[$platform]="https://downloads.cursor.com/sand/stable/$target/$latestVersion/Grok_Bot_$latestVersion.dmg"
  else
    urls[$platform]=$(jq -er '.url' <<< "$release")
  fi

  source=$(nix-prefetch-url "${urls[$platform]}")
  hashes[$platform]=$(nix-hash --to-sri --type sha256 "$source")
done

for platform in "${!platforms[@]}"; do
  # Linux URLs contain a build ID as well as the version, so replace them in full.
  newUrl=""
  if [[ "$platform" == *-linux ]]; then
    newUrl="${urls[$platform]}"
  fi
  update-source-version grok-bot "$latestVersion" "${hashes[$platform]}" "$newUrl" \
    --system="$platform" \
    --source-key="passthru.sources.$platform" \
    --ignore-same-version
done
