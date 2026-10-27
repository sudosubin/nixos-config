#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils nix-update nodejs_24
set -eu -o pipefail

latestVersion=$(
  curl -fsSL \
    -H "Accept: application/vnd.github+json" \
    ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
    "https://api.github.com/repos/material-extensions/vscode-material-icon-theme/releases/latest" \
      | jq -er '.tag_name | ltrimstr("v")'
)
currentVersion=$(nix eval --raw -f . material-icon-theme.version)

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# upstream's lockfile lacks resolved URLs, so regenerate it from the release's package.json
curl -fsSL \
  -H "Accept: application/vnd.github.raw" \
  ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
  "https://api.github.com/repos/material-extensions/vscode-material-icon-theme/contents/package.json?ref=v$latestVersion" \
  -o "$tmp/package.json"
(cd "$tmp" && npm install --package-lock-only --ignore-scripts --no-audit --no-fund --registry=https://registry.npmjs.org/)
cp "$tmp/package-lock.json" "$(dirname "$0")/package-lock.json"

nix-update --version "$latestVersion" material-icon-theme
