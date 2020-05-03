#!/bin/bash

# Directory
current_dir="$(dirname "${BASH_SOURCE[0]}")"
app_dir="$(dirname "$(dirname "$current_dir")")"

# shellcheck source=01-software/install.sh
source "$app_dir/src/scripts/01-software/install.sh"
