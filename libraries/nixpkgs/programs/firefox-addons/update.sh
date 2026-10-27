#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils gnused nix
set -eu -o pipefail

slug="$1"
file="libraries/nixpkgs/programs/firefox-addons/$slug/default.nix"

release=$(curl -fsSL "https://addons.mozilla.org/api/v5/addons/addon/$slug/" | jq -c '.current_version')
latestVersion=$(jq -er '.version' <<< "$release")
currentVersion=$(sed -nE 's/^  version = "(.*)";$/\1/p' "$file")

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

url=$(jq -er '.file.url' <<< "$release")
hex=$(jq -er '.file.hash | select(startswith("sha256:")) | ltrimstr("sha256:")' <<< "$release")
hash=$(nix hash convert --hash-algo sha256 --to sri "$hex")

# the AMO file id changes on every release, so the whole url is replaced
sed -i -E \
  -e "s|^  version = \".*\";$|  version = \"$latestVersion\";|" \
  -e "s|^  url = \".*\";$|  url = \"$url\";|" \
  -e "s|^  sha256 = \".*\";$|  sha256 = \"$hash\";|" \
  "$file"
