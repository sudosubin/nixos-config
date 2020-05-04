#!/bin/bash

# Directory
current_dir="$(dirname "${BASH_SOURCE[0]}")"
app_dir="$(dirname "$(dirname "$current_dir")")"

# shellcheck source=01-software/install.sh
source "$app_dir/src/scripts/01-software/install.sh"

# shellcheck source=02-basic-installation/install.sh
source "$app_dir/src/scripts/02-basic-installation/install.sh"

# shellcheck source=03-appearance/install.sh
source "$app_dir/src/scripts/03-appearance/install.sh"

# shellcheck source=04-tweaks/install.sh
source "$app_dir/src/scripts/04-tweaks/install.sh"
