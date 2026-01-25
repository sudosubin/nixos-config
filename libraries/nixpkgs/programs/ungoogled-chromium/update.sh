#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils common-updater-scripts nix-prefetch
set -eu -o pipefail

# Get latest ungoogled-chromium-macos release
latestTag=$(curl -s https://api.github.com/repos/ungoogled-software/ungoogled-chromium-macos/releases/latest | jq -r ".tag_name")
latestVersion="${latestTag%-*}"
currentVersion=$(nix eval --raw -f . ungoogled-chromium.version)

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

declare -A platforms=( [x86_64-darwin]="x86_64" [aarch64-darwin]="arm64" )

for platform in "${!platforms[@]}"; do
  arch="${platforms[$platform]}"
  url="https://github.com/ungoogled-software/ungoogled-chromium-macos/releases/download/${latestTag}/ungoogled-chromium_${latestTag}_${arch}-macos.dmg"
  source=$(nix-prefetch-url "$url")
  hash=$(nix-hash --to-sri --type sha256 "$source")

  update-source-version ungoogled-chromium "$latestVersion" "$hash" "$url" \
    --system="$platform" \
    --source-key="passthru.sources.$platform" \
    --ignore-same-version
done
