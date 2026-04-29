#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils common-updater-scripts
set -eu -o pipefail

latestVersion=$(
  curl -fsSL \
    -H "Accept: application/vnd.github+json" \
    ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
    "https://api.github.com/repos/Kotlin/kotlin-lsp/releases/latest" \
      | jq -er '.tag_name | sub("^kotlin-lsp/v"; "")'
)
currentVersion=$(nix eval --raw -f . kotlin-lsp.version)

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

declare -A filenames=(
  [x86_64-linux]="kotlin-server-$latestVersion.tar.gz"
  [aarch64-linux]="kotlin-server-$latestVersion-aarch64.tar.gz"
  [x86_64-darwin]="kotlin-server-$latestVersion.sit"
  [aarch64-darwin]="kotlin-server-$latestVersion-aarch64.sit"
)

for platform in "${!filenames[@]}"; do
  filename=${filenames[$platform]}
  url="https://download-cdn.jetbrains.com/kotlin-lsp/$latestVersion/$filename"
  source=$(nix-prefetch-url --unpack --name "${filename/%.sit/.zip}" "$url")
  hash=$(nix-hash --to-sri --type sha256 "$source")
  update-source-version kotlin-lsp "$latestVersion" "$hash" \
    --system="$platform" \
    --source-key="passthru.sources.$platform" \
    --ignore-same-version
done
