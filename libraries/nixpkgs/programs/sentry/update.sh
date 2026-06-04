#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils common-updater-scripts yq-go
set -eu -o pipefail

latestVersion=$(
  curl -fsSL \
    -H "Accept: application/vnd.github+json" \
    ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
    "https://api.github.com/repos/getsentry/cli/releases/latest" \
      | jq -er ".tag_name"
)
currentVersion=$(nix eval --raw -f . sentry.version)

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# Update for src
curl -fsSL \
  ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
  "https://api.github.com/repos/getsentry/cli/tarball/$latestVersion" -o "$tmp/src.tar.gz"
hash=$(nix-hash --to-sri --type sha256 "$(nix-prefetch-url --unpack "file://$tmp/src.tar.gz")")
update-source-version sentry "$latestVersion" "$hash" --ignore-same-version

# Update for node_modules
update-source-version sentry --source-key=node_modules --ignore-same-version

# Update for openapi_spec
sentryApiVersion=$(
  curl -fsSL \
    -H "Accept: application/vnd.github.raw" \
    ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
    "https://api.github.com/repos/getsentry/cli/contents/pnpm-lock.yaml?ref=$latestVersion" \
    | yq -r '.importers["."] | (.dependencies["@sentry/api"].version // .devDependencies["@sentry/api"].version) | sub("[(].*", "")'
)
curl -fsSL \
  -H "Accept: application/vnd.github.raw" \
  ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
  "https://api.github.com/repos/getsentry/sentry-api-schema/contents/openapi-derefed.json?ref=$sentryApiVersion" \
  -o "$tmp/openapi.json"
hash=$(nix-hash --to-sri --type sha256 "$(nix-prefetch-url "file://$tmp/openapi.json")")
update-source-version sentry "$sentryApiVersion" "$hash" \
  --version-key=sentryApiVersion \
  --source-key=openapi_spec \
  --ignore-same-version
