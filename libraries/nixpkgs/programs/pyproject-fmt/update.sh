#!/usr/bin/env nix-shell
#!nix-shell -i bash -p curl jq coreutils nix-prefetch-git common-updater-scripts
set -eu -o pipefail

latestVersion=$(
  curl -s https://api.github.com/repos/tox-dev/toml-fmt/releases \
    | jq -r '[.[] | select(.tag_name | startswith("pyproject-fmt/")) | .tag_name | sub("^pyproject-fmt/"; "")] | first'
)
currentVersion=$(nix eval --raw -f . pyproject-fmt.version)

echo "latest  version: $latestVersion"
echo "current version: $currentVersion"

if [[ "$latestVersion" == "$currentVersion" ]]; then
  echo "package is up-to-date"
  exit 0
fi

hash=$(
  nix-prefetch-git https://github.com/tox-dev/toml-fmt \
    --rev "pyproject-fmt/$latestVersion" \
    --no-add-path \
    --quiet \
    | jq -r ".hash"
)
update-source-version pyproject-fmt "$latestVersion" "$hash"
