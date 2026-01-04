#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils common-updater-scripts
set -eu -o pipefail

latestVersion=$(curl -s https://api.github.com/repos/Kotlin/kotlin-lsp/releases/latest | jq -r '.tag_name | sub("^kotlin-lsp/v"; "")')
currentVersion=$(nix eval --raw -f . kotlin-lsp.version)

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

declare -A platforms=( [x86_64-linux]="linux-x64" [aarch64-linux]="linux-aarch64" [x86_64-darwin]="mac-x64" [aarch64-darwin]="mac-aarch64" )

for platform in "${!platforms[@]}"; do
  url="https://download-cdn.jetbrains.com/kotlin-lsp/$latestVersion/kotlin-lsp-$latestVersion-${platforms[$platform]}.zip"
  source=$(nix-prefetch-url "$url" --unpack)
  hash=$(nix-hash --to-sri --type sha256 "$source")
  update-source-version kotlin-lsp "$latestVersion" "$hash" \
    --system="$platform" \
    --source-key="passthru.sources.$platform" \
    --ignore-same-version
done
