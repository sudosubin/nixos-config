#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils common-updater-scripts
set -eu -o pipefail

# Fetch latest version from npm registry
latestVersion=$(curl -s https://registry.npmjs.org/@anthropic-ai/claude-code/latest | jq -r ".version")
currentVersion=$(nix eval --raw -f . claude-code-bin.version)

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

declare -A platforms=(
  [x86_64-linux]="linux-x64"
  [aarch64-linux]="linux-arm64"
  [x86_64-darwin]="darwin-x64"
  [aarch64-darwin]="darwin-arm64"
)

for platform in "${!platforms[@]}"; do
  url="https://storage.googleapis.com/claude-code-dist-86c565f3-f756-42ad-8dfa-d59b1c096819/claude-code-releases/$latestVersion/${platforms[$platform]}/claude"
  source=$(nix-prefetch-url "$url")
  hash=$(nix-hash --to-sri --type sha256 "$source")
  update-source-version claude-code-bin "$latestVersion" "$hash" \
    --system="$platform" \
    --source-key="passthru.sources.$platform" \
    --ignore-same-version
done
