#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils common-updater-scripts perl
set -eu -o pipefail

latestVersion=$(
  curl -fsSL \
    -H "Accept: application/vnd.github+json" \
    ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
    "https://api.github.com/repos/getsentry/cli/releases/latest" \
      | jq -er ".tag_name"
)
currentVersion="$UPDATE_NIX_OLD_VERSION"
file="$(nix-instantiate --eval -E 'with import ./. {}; (builtins.unsafeGetAttrPos "version" '"${UPDATE_NIX_ATTR_PATH}"').file' | tr -d '"')"
fakeHash=$(nix eval --raw -f . lib.fakeHash)

replaceOutputHash() {
  local subpackage="$1"
  local targetHash="$2"

  TARGET_HASH="$targetHash" SUBPACKAGE="$subpackage" perl -0pi -e '
    my $prefix = quotemeta($ENV{SUBPACKAGE} . q( = stdenvNoCC.mkDerivation {));
    s{($prefix.*?outputHash = ")[^"]+(";)}{$1 . $ENV{TARGET_HASH} . $2}se;
  ' "$file"
}

updateOutputHash() {
  local subpackage="$1"
  local currentHash
  local newHash

  currentHash=$(nix eval --raw -f . "$UPDATE_NIX_ATTR_PATH.$subpackage.outputHash")

  replaceOutputHash "$subpackage" "$fakeHash"
  newHash="$(nix-build -A "$UPDATE_NIX_ATTR_PATH.$subpackage" --no-out-link 2>&1 | tail -n3 | grep 'got:' | cut -d: -f2- | xargs echo || true)"

  if [[ -z "$newHash" ]]; then
    replaceOutputHash "$subpackage" "$currentHash"
    echo "failed to retrieve $subpackage hash" >&2
    exit 1
  fi

  replaceOutputHash "$subpackage" "$newHash"
  echo "$subpackage hash: $newHash"
}

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

srcUrl="https://github.com/getsentry/cli/archive/refs/tags/$latestVersion.tar.gz"
srcHash=$(nix-hash --to-sri --type sha256 "$(nix-prefetch-url "$srcUrl" --unpack)")

update-source-version "$UPDATE_NIX_ATTR_PATH" "$latestVersion" "$srcHash" --ignore-same-version

# Update node_modules first because api_schema depends on it.
# Replace hashes by derivation block to avoid touching both hashes when they are equal.
for subpackage in node_modules api_schema; do
  updateOutputHash "$subpackage"
done
