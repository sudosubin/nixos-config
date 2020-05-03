#!/bin/bash

# Directory
current_dir="$(dirname "${BASH_SOURCE[0]}")"
script_dir="$(dirname "$current_dir")"
app_dir="$(dirname "$(dirname "$(dirname "$script_dir")")")"

# shellcheck source=global-theme.sh
source "$script_dir/libs/global-theme.sh"

# shellcheck source=window-decorations.sh
source "$script_dir/libs/window-decorations.sh"

# shellcheck source=colors.sh
source "$script_dir/libs/colors.sh"
